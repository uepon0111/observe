import requests
import json
import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

# 設定
API_IDS_URL = "https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/ids"
API_POST_URL = "https://minorisuzuki.api.app.c-rayon.com/api/public/tl_posts/"
DATA_FILE = "timeline.json"

def main():
    # すでに保存されているデータを読み込む
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            known_ids = {post['id'] for post in saved_data}
    else:
        saved_data = []
        known_ids = set()

    # 日本標準時(JST)の現在時刻を起点にする
    JST = timezone(timedelta(hours=+9), 'JST')
    current_from = datetime.now(JST).isoformat(timespec='milliseconds')
    
    new_posts = []
    
    print("データ取得を開始します...")
    
    while True:
        # fromパラメータをURLエンコードして一覧を取得
        encoded_from = quote(current_from)
        res = requests.get(f"{API_IDS_URL}?from={encoded_from}")
        if res.status_code != 200:
            print(f"一覧の取得に失敗しました: {res.status_code}")
            break
            
        data = res.json().get("data", [])
        if not data:
            print("これ以上過去の投稿はありません。")
            break
            
        all_known = True # 今回取得した10件がすべて既知かどうか
        
        for item in data:
            post_id = item["id"]
            published_at = item["attributes"]["publishedAt"]
            
            # すでに取得済みの投稿に到達したらスキップ
            if post_id in known_ids:
                # from更新用に日付は進めておく
                current_from = published_at
                continue
                
            all_known = False
            print(f"新規投稿を取得中: {published_at}")
            
            # 投稿の詳細を取得
            detail_res = requests.get(f"{API_POST_URL}{post_id}")
            if detail_res.status_code == 200:
                detail_json = detail_res.json()
                
                # テキストの抽出
                text = detail_json.get("data", {}).get("attributes", {}).get("text", "")
                
                # 画像URLの抽出
                images = []
                for inc in detail_json.get("included", []):
                    if inc.get("type") == "photo":
                        img_url = inc.get("attributes", {}).get("urls", {}).get("original")
                        if img_url:
                            images.append(img_url)
                
                # データをリストに追加
                new_posts.append({
                    "id": post_id,
                    "publishedAt": published_at,
                    "text": text,
                    "images": images
                })
                known_ids.add(post_id)
            
            time.sleep(1) # APIサーバーへの負荷軽減のためのウェイト
            
            # 次の取得の起点(from)を、このループの最後の投稿日時に更新
            current_from = published_at
            
        # 取得した10件がすべて保存済み（既知）なら、過去の探索を終了する
        if all_known:
            print("既存の投稿に追いついたため、取得を終了します。")
            break

    if new_posts:
        # 新しい投稿を追加して、投稿日時の降順（新しい順）でソート
        saved_data.extend(new_posts)
        saved_data.sort(key=lambda x: x["publishedAt"], reverse=True)
        
        # JSONファイルに保存
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(saved_data, f, ensure_ascii=False, indent=2)
        print(f"新たに {len(new_posts)} 件の投稿を保存しました！")
    else:
        print("新しい投稿はありませんでした。")

if __name__ == "__main__":
    main()
