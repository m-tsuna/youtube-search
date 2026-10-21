"""
YouTube 動画検索プログラム（課題：YouTube API）

YouTube Data API を使い、入力したキーワードで動画を検索して、
見つかった動画のタイトルと URL をコンソール（ターミナル）に表示する。

使い方：ターミナルで  python main.py  を実行する。
"""

import html
import os
import sys
from pathlib import Path

import httplib2
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================
# 設定（ここをまとめて書いておく）
# ============================================================

# このプログラム（main.py）が置いてあるフォルダ
BASE_DIR = Path(__file__).resolve().parent

# API キーを書いておくファイルと、その中の項目名
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE_FILE = BASE_DIR / ".env.example"
API_KEY_NAME = "YOUTUBE_API_KEY"

# 1回の検索で表示する動画の数の上限（1〜50 の間で変えられる）
# 見られない動画などを YouTube が除くため、これより少なく返ってくることがある
MAX_RESULTS = 10

# 選べる並び順。番号: (画面に出す名前, API に渡す値)
# 何も入力せずに Enter を押したときは、DEFAULT_ORDER の番号を使う
ORDER_CHOICES = {
    "1": ("関連度順", "relevance"),
    "2": ("新しい順", "date"),
}
DEFAULT_ORDER = "1"

# 動画のページの URL の形。{video_id} のところに動画IDが入る
VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"

# 検索結果の区切り線
SEPARATOR = "-" * 30


# ============================================================
# F1 API キーの読み込み
# ============================================================
def load_api_key():
    """
    .env の YOUTUBE_API_KEY から API キーを読み込んで返す。
    .env が無い・キーが空の場合は、理由を表示して終了する（F5）。
    """
    # .env の中身を「環境変数」（プログラムが読める設定値）として読み込む
    load_dotenv(ENV_FILE)
    api_key = os.getenv(API_KEY_NAME, "").strip()

    if not api_key:
        show_error_and_exit(
            f"API キーが設定されていません。\n"
            f"{ENV_EXAMPLE_FILE.name} をコピーして「{ENV_FILE.name}」という名前にし、\n"
            f"{API_KEY_NAME}= の後ろに API キーを書いてください。\n"
            f"置き場所: {BASE_DIR}"
        )
    return api_key


# ============================================================
# F2 キーワード・並び順の入力
# ============================================================
def ask_keyword():
    """
    検索キーワードを入力してもらう。空欄なら、もう一度聞く。
    """
    while True:
        keyword = input("検索キーワードを入力してください: ").strip()
        if keyword:
            return keyword
        print("キーワードが空です。キーワードを入力してください。")


def ask_order():
    """
    並び順を番号で選んでもらい、(画面に出す名前, API に渡す値) を返す。
    何も入力せずに Enter なら関連度順。番号以外なら、もう一度聞く。
    """
    choices = "  ".join(f"{number}. {name}" for number, (name, _) in ORDER_CHOICES.items())
    while True:
        print(f"並び順を選んでください: {choices}")
        answer = input(f"番号（Enter だけなら {ORDER_CHOICES[DEFAULT_ORDER][0]}）: ").strip()
        if answer == "":
            answer = DEFAULT_ORDER
        if answer in ORDER_CHOICES:
            return ORDER_CHOICES[answer]
        print(f"{'、'.join(ORDER_CHOICES)} のどれかを入力してください。")


# ============================================================
# F3 動画の検索
# ============================================================
def search_videos(api_key, keyword, order):
    """
    YouTube Data API の search.list で動画を検索し、見つかった動画の一覧を返す。

    - part="snippet"   … タイトルなどの基本情報も一緒にもらう
    - type="video"     … チャンネルや再生リストを除き、動画だけにする
    - order            … 並び順（ask_order で選んだもの）
    - maxResults       … 何件もらうか（設定の MAX_RESULTS）
    API キーを渡すだけで使える（ログインは要らない）。
    """
    # YouTube を操作するための「サービス」を作る
    youtube = build("youtube", "v3", developerKey=api_key)

    response = youtube.search().list(
        q=keyword,
        part="snippet",
        type="video",
        order=order,
        maxResults=MAX_RESULTS,
    ).execute()

    # 返事の "items" に、見つかった動画が1件ずつ入っている
    return response.get("items", [])


# ============================================================
# F4 結果の表示
# ============================================================
def show_results(keyword, order_name, videos):
    """
    見つかった動画の番号・タイトル・URL を表示する。
    1件も無ければ、その旨を表示する。
    """
    if not videos:
        print("動画が見つかりませんでした。")
        return

    print()
    print(f"「{keyword}」の検索結果（{order_name}・{len(videos)}件）")
    print(SEPARATOR)
    for number, video in enumerate(videos, start=1):
        # タイトルは &amp; や &#39; の形で届くことがあるので、元の記号に戻す
        title = html.unescape(video["snippet"]["title"])
        url = VIDEO_URL.format(video_id=video["id"]["videoId"])
        print(f"{number}. {title}")
        print(f"   {url}")
    print(SEPARATOR)


# ============================================================
# F5 エラー表示
# ============================================================
def show_error_and_exit(message):
    """
    原因が分かる日本語のエラーメッセージを表示して、プログラムを終了する。
    """
    print(f"エラー: {message}", file=sys.stderr)
    sys.exit(1)


def explain_http_error(error):
    """
    Google とのやりとりで起きたエラー（HttpError）を、日本語の説明に直して返す。
    """
    # Google から届いたエラーの中身（英語の理由が書いてある）
    content = error.content.decode("utf-8", errors="replace")

    # 1日の割り当て（クォータ）を使い切った
    if "quotaExceeded" in content:
        return (
            "今日の検索できる回数（割り当て）を使い切りました。\n"
            "割り当ては毎日、太平洋時間の0時（日本時間の16時か17時）にリセットされます。\n"
            f"詳細: {error.reason}"
        )
    # API キーが正しくない
    if error.status_code == 400 and "API key" in content:
        return (
            "API キーが正しくありません。\n"
            f"{ENV_FILE.name} の {API_KEY_NAME} が、Google Cloud Console で作ったキーと同じか確認してください。\n"
            f"詳細: {error.reason}"
        )
    # YouTube Data API が有効でない、またはキーの制限で使えない
    if error.status_code == 403:
        return (
            "YouTube Data API を使う許可がありません。\n"
            "Google Cloud Console で次を確認してください。\n"
            "  ・「API とサービス」→「ライブラリ」で「YouTube Data API v3」が有効になっているか\n"
            "  ・「認証情報」の API キーの制限に「YouTube Data API v3」が入っているか\n"
            f"詳細: {error.reason}"
        )
    return (
        "YouTube とのやりとりに失敗しました。\n"
        f"ステータスコード: {error.status_code}\n"
        f"詳細: {error.reason}"
    )


# ============================================================
# メインの処理（上の関数を順番に呼ぶ）
# ============================================================
def main():
    """
    プログラム全体の流れ：
    API キーの読み込み → キーワード・並び順の入力 → 動画の検索 → 結果の表示
    """
    try:
        # F1 API キーの読み込み（検索より先に確かめる）
        api_key = load_api_key()

        # F2 キーワード・並び順の入力
        keyword = ask_keyword()
        order_name, order = ask_order()

        # F3 動画の検索
        videos = search_videos(api_key, keyword, order)

        # F4 結果の表示
        show_results(keyword, order_name, videos)

    except HttpError as error:
        # Google とのやりとりで失敗した（F5）
        show_error_and_exit(explain_http_error(error))
    except (httplib2.HttpLib2Error, OSError) as error:
        # インターネットにつながらない など（F5）
        show_error_and_exit(
            "YouTube につながりませんでした。インターネット接続を確認してください。\n"
            f"詳細: {error}"
        )
    except (KeyboardInterrupt, EOFError):
        # Ctrl + C で途中でやめた場合
        print("\n中断しました。")
        sys.exit(1)


# このファイルを直接実行したときだけ main() を動かす
if __name__ == "__main__":
    main()
