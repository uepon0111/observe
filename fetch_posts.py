import requests
import json
import os

# APIエンドポイント
IDS_URL = "https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/ids"
BASE_POST_URL = "https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/"

# 保存用ファイル
HISTORY_FILE = "history.json"
OUTPUT_FILE = "posts.md"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def main():
    history = load_history()
    
    # ID一覧を取得
    res = requests.get(IDS_URL)
    if res.status_code != 200:
        print("APIの取得に失敗しました。")
        return
    
    data = res.json()
    new_posts = []
    
    # ID一覧から未取得のものだけを抽出
    for item in data.get("data", []):
        post_id = item.get("id")
        if post_id not in history:
            # 個別投稿のデータを取得
            post_res = requests.get(BASE_POST_URL + post_id)
            if post_res.status_code == 200:
                post_data = post_res.json().get("data", {}).get("attributes", {})
                text = post_data.get("text", "")
                published_at = post_data.get("publishedAt", "")
                
                new_posts.append({
                    "id": post_id,
                    "date": published_at,
                    "text": text
                })
                history.append(post_id)
    
    # 新しい投稿があればMarkdownファイルに追記
    if new_posts:
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            # 古い順に保存したい場合は reversed(new_posts) を使用
            for post in new_posts:
                f.write(f"## {post['date']}\n\n")
                f.write(f"{post['text']}\n\n")
                f.write(f"---\n\n")
        
        save_history(history)
        print(f"{len(new_posts)} 件の新しい投稿を保存しました。")
    else:
        print("新しい投稿はありませんでした。")

if __name__ == "__main__":
    main()
