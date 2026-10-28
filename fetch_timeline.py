import requests
import json
import time
import os
from datetime import datetime, timezone
from urllib.parse import quote

# 保存先のファイル名
DATA_FILE = "timeline_data.jsonl"

def get_post_ids(from_date):
    # APIの仕様上 + がスペースに変換されないようにURLエンコードが必要な場合があります
    encoded_date = quote(from_date)
    url = f"https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/ids?from={encoded_date}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("data", [])

def get_post_detail(post_id):
    url = f"https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/{post_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def main():
    # 既に取得したIDを読み込み、重複取得と過去投稿への不要な通信を防ぐ
    fetched_ids = set()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                fetched_ids.add(data["id"])

    # 取得開始の基準日（最初は現在時刻から遡る）
    # 例: "2026-03-11T00:00:00.000+09:00"
    current_from = datetime.now(timezone.utc).astimezone().isoformat()

    print("データ取得を開始します。")

    while True:
        print(f"ID一覧を取得中 (from: {current_from})")
        post_ids_data = get_post_ids(current_from)

        if not post_ids_data:
            print("これ以上古い投稿はありません。")
            break

        # 新しい投稿から順に確認できるよう、公開日時の降順にする
        post_ids_data.sort(
            key=lambda item: item["attributes"]["publishedAt"],
            reverse=True
        )

        oldest_date = None
        stop_at_existing_post = False

        for item in post_ids_data:
            post_id = item["id"]
            published_at = item["attributes"]["publishedAt"]

            # ページ内で最も古い日時を次回の基準日用に記録
            if oldest_date is None or published_at < oldest_date:
                oldest_date = published_at

            # 新しい順に確認しているため、取得済み投稿に到達したら
            # それより古い投稿の詳細取得・ID一覧取得を行わず終了する
            if post_id in fetched_ids:
                print(f"取得済みの投稿に到達しました: {post_id}")
                stop_at_existing_post = True
                break

            print(f"投稿詳細を取得中: {post_id}")
            detail = get_post_detail(post_id)

            # 本文と画像URLの抽出
            post_data = detail.get("data", {})
            included = detail.get("included", [])

            text = post_data.get("attributes", {}).get("text", "")
            images = []

            for inc in included:
                if inc.get("type") == "photo":
                    img_url = inc.get("attributes", {}).get("urls", {}).get("original")
                    if img_url:
                        images.append(img_url)

            # 保存用データの作成
            save_data = {
                "id": post_id,
                "publishedAt": published_at,
                "text": text,
                "images": images
            }

            # ファイルに追記保存
            with open(DATA_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(save_data, ensure_ascii=False) + "\\n")

            fetched_ids.add(post_id)
            time.sleep(1)  # APIサーバーに負荷をかけないよう1秒待機

        if stop_at_existing_post:
            print("取得済みの投稿より古い投稿は取得せず終了します。")
            break

        # 取得済み投稿がまだ見つからない場合のみ、次の過去ページへ進む
        if oldest_date is None:
            print("投稿日時を確認できないため終了します。")
            break

        current_from = oldest_date
        time.sleep(1)

if __name__ == "__main__":
    main()
