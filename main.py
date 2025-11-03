# main.py
import requests
import time
import json
import os
from datetime import datetime

# 환경 변수에서 설정값 가져오기 (Render에서 설정)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '300'))  # 기본 5분

class KoreatechJobNotifier:
    def __init__(self):
        self.seen_posts = set()
        self.load_seen_posts()
        print(f"✅ 봇 초기화 완료")
        print(f"📱 텔레그램 Chat ID: {TELEGRAM_CHAT_ID}")
    
    def load_seen_posts(self):
        """이전에 확인한 게시글 ID 불러오기"""
        try:
            with open('seen_posts.json', 'r', encoding='utf-8') as f:
                self.seen_posts = set(json.load(f))
            print(f"📋 이전 게시글 {len(self.seen_posts)}개 로드됨")
        except FileNotFoundError:
            print("📋 새로 시작: 이전 기록 없음")
            self.seen_posts = set()
    
    def save_seen_posts(self):
        """확인한 게시글 ID 저장"""
        with open('seen_posts.json', 'w', encoding='utf-8') as f:
            json.dump(list(self.seen_posts), f, ensure_ascii=False)
    
    def get_job_posts(self):
        """학생생활 게시판에서 아르바이트 공고 가져오기"""
        try:
            # KOIN API 사용 (실제 엔드포인트는 API 문서 확인 필요)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # 방법 1: KOIN API 사용
            response = requests.get(
                "https://api.koreatech.in/articles",
                params={
                    "board_id": 3,  # 학생생활 게시판 ID (확인 필요)
                    "limit": 20
                },
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                # '아르바이트' 키워드 필터링
                job_posts = []
                keywords = ['아르바이트', '알바', '구인', '구함', '모집']
                
                for article in articles:
                    title = article.get('title', '').lower()
                    if any(keyword in title for keyword in keywords):
                        job_posts.append(article)
                
                return job_posts
            else:
                print(f"⚠️ API 응답 오류: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"❌ 게시글 가져오기 실패: {e}")
            return []
    
    def send_telegram_message(self, post):
        """텔레그램으로 알림 전송"""
        title = post.get('title', '제목 없음')
        author = post.get('author', '익명')
        created_at = post.get('created_at', '')
        post_id = post.get('id', '')
        
        message = f"""🔔 새로운 아르바이트 공고!

📌 {title}
👤 작성자: {author}
📅 {created_at}

🔗 https://koreatech.in/board/{post_id}
"""
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ 알림 전송 성공: {title[:30]}...")
            return True
        
        except Exception as e:
            print(f"❌ 텔레그램 전송 실패: {e}")
            return False
    
    def check_new_posts(self):
        """새 게시글 확인 및 알림"""
        posts = self.get_job_posts()
        new_posts = []
        
        for post in posts:
            post_id = str(post.get('id', ''))
            if post_id and post_id not in self.seen_posts:
                new_posts.append(post)
                self.seen_posts.add(post_id)
        
        # 새 게시글이 있으면 알림 전송
        for post in new_posts:
            self.send_telegram_message(post)
            time.sleep(2)  # API 요청 제한 방지
        
        # 확인한 게시글 저장
        if new_posts:
            self.save_seen_posts()
        
        return len(new_posts)
    
    def run(self):
        """메인 루프 - 계속 실행"""
        print("=" * 50)
        print("🚀 한국기술교육대학교 아르바이트 알림 봇 시작!")
        print(f"⏰ 체크 주기: {CHECK_INTERVAL}초 ({CHECK_INTERVAL//60}분)")
        print("=" * 50)
        
        # 시작 알림
        try:
            start_message = "🤖 아르바이트 알림 봇이 시작되었습니다!\n24시간 자동으로 새 공고를 확인합니다."
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": start_message}, timeout=10)
        except:
            pass
        
        while True:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{current_time}] 게시판 확인 중...")
                
                new_count = self.check_new_posts()
                
                if new_count > 0:
                    print(f"✅ 새 게시글 {new_count}개 발견 및 알림 전송!")
                else:
                    print("💤 새 게시글 없음")
                
                print(f"⏰ {CHECK_INTERVAL}초 후 다시 확인...")
                time.sleep(CHECK_INTERVAL)
            
            except KeyboardInterrupt:
                print("\n👋 프로그램 종료")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                print("⏰ 60초 후 재시도...")
                time.sleep(60)

if __name__ == "__main__":
    # 환경 변수 확인
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 오류: TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정해주세요!")
        exit(1)
    
    notifier = KoreatechJobNotifier()
    notifier.run()