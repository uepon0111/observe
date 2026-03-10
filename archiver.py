import os
import json
import time
import requests
from datetime import datetime

# APIエンドポイント
IDS_URL = "https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/ids"
POST_URL = "https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/{post_id}"

STATE_FILE = "state.json"
ARCHIVE_DIR = "archive"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded_ids": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def fetch_ids(from_date=None):
    params = {}
    if from_date:
        params["from"] = from_date
    res = requests.get(IDS_URL, params=params)
    res.raise_for_status()
    return res.json().get("data", [])

def fetch_post(post_id):
    res = requests.get(POST_URL.format(post_id=post_id))
    res.raise_for_status()
    return res.json()

def save_post_as_md(post_data):
    data = post_data.get("data", {})
    included = post_data.get("included", [])
    
    post_id = data.get("id")
    attrs = data.get("attributes", {})
    text = attrs.get("text", "")
    published_at = attrs.get("publishedAt", "")
    
    # 画像URLの抽出
    photo_urls = []
    for inc in included:
        if inc.get("type") == "photo":
            urls = inc.get("attributes", {}).get("urls", {})
            if "original" in urls:
                photo_urls.append(urls["original"])

    # ファイル名用の日付文字列生成
    try:
        dt = datetime.fromisoformat(published_at)
        date_str = dt.strftime("%Y-%m-%d_%H%M%S")
        readable_date = dt.strftime("%Y年%m月%d日 %H:%M:%S")
    except ValueError:
        date_str = "unknown_date"
        readable_date = published_at

    filename = f"{date_str}_{post_id}.md"
    filepath = os.path.join(ARCHIVE_DIR, filename)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # Markdownとして保存
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# 投稿日時: {readable_date}\n\n")
        f.write(text + "\n\n")
        if photo_urls:
            f.write("## 画像\n")
            for url in photo_urls:
                f.write(f"![image]({url})\n")

def main():
    state = load_state()
    downloaded_ids = set(state["downloaded_ids"])
    
    current_from = None
    has_more = True
    new_downloads = 0

    while has_more:
        print(f"リスト取得中... from={current_from}")
        ids_data = fetch_ids(from_date=current_from)
        
        if not ids_data:
            break

        oldest_date = None
        all_already_downloaded = True

        for item in ids_data:
            post_id = item.get("id")
            published_at = item.get("attributes", {}).get("publishedAt")
            
            # 取得した10件の中で一番古い日付を特定する
            if oldest_date is None or published_at < oldest_date:
                oldest_date = published_at

            # 未取得の投稿であれば詳細を取得して保存
            if post_id not in downloaded_ids:
                all_already_downloaded = False
                print(f"投稿詳細を取得中: {post_id}")
                post_data = fetch_post(post_id)
                save_post_as_md(post_data)
                
                downloaded_ids.add(post_id)
                new_downloads += 1
                
                # サーバー負荷軽減のため1秒待機（重要）
                time.sleep(1)

        # 今回の10件がすべて取得済みだった場合、これ以上過去に遡る必要はない
        if all_already_downloaded:
            print("過去の取得済み投稿に到達したため、遡りを停止します。")
            break

        # 次のページ（さらに古い投稿）へ
        current_from = oldest_date
        time.sleep(1)

    # 取得したIDリストを保存
    state["downloaded_ids"] = list(downloaded_ids)
    save_state(state)
    print(f"完了! {new_downloads} 件の新しい投稿をアーカイブしました。")

if __name__ == "__main__":
    main()
