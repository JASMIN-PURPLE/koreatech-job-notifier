import requests
import time
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

# 환경 변수
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '180'))  # 3분

class KoreatechJobNotifier:
    def __init__(self):
        self.seen_posts = set()
        self.base_url = "https://portal.koreatech.ac.kr"
        self.board_url = f"{self.base_url}/ctt/bb/bulletin?b=21"
        self.load_seen_posts()
        print(f"✅ 봇 초기화 완료")
        print(f"📱 텔레그램 Chat ID: {TELEGRAM_CHAT_ID}")
        print(f"🌐 모니터링 URL: {self.board_url}")
    
    def load_seen_posts(self):
        try:
            with open('seen_posts.json', 'r', encoding='utf-8') as f:
                self.seen_posts = set(json.load(f))
            print(f"📋 이전 게시글 {len(self.seen_posts)}개 로드됨")
        except FileNotFoundError:
            print("📋 새로 시작: 이전 기록 없음")
            self.seen_posts = set()
    
    def save_seen_posts(self):
        with open('seen_posts.json', 'w', encoding='utf-8') as f:
            json.dump(list(self.seen_posts), f, ensure_ascii=False)
    
    def get_job_posts(self):
        """학생생활 게시판에서 아르바이트 분류 게시글 가져오기"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            
            # 1. 먼저 API 시도
            try:
                api_url = f"{self.base_url}/api/bulletin/list"
                response = requests.get(
                    api_url,
                    params={'b': '21', 'limit': 30},
                    headers=headers,
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"📡 API 응답 성공")
                    return self.parse_api_response(data)
            except Exception as e:
                print(f"⚠️ API 시도 실패: {e}")
            
            # 2. API 실패 시 HTML 파싱
            print(f"🌐 HTML 페이지 파싱 시도...")
            response = requests.get(
                self.board_url,
                headers=headers,
                timeout=15
            )
            
            print(f"📡 페이지 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                return self.parse_html_response(response.text)
            else:
                print(f"⚠️ 페이지 로드 실패: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"❌ 게시글 가져오기 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def parse_api_response(self, data):
        """API 응답 파싱"""
        job_posts = []
        articles = data.get('list', data.get('articles', data.get('data', [])))
        
        for article in articles:
            category = article.get('category', article.get('classification', ''))
            if '아르바이트' in str(category):
                job_posts.append({
                    'id': article.get('id', article.get('no', '')),
                    'title': article.get('title', '제목 없음'),
                    'author': article.get('author', article.get('writer', '익명')),
                    'date': article.get('date', article.get('created_at', '')),
                    'category': category
                })
                print(f"  ✓ 발견: [{category}] {article.get('title', '')}")
        
        return job_posts
    
    def parse_html_response(self, html):
        """HTML 파싱 (API가 없을 경우)"""
        job_posts = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 게시글 목록 찾기 (실제 HTML 구조에 맞게 조정 필요)
        # 일반적인 게시판 구조 패턴들
        possible_selectors = [
            'table.board-list tbody tr',
            'ul.board-list li',
            'div.board-item',
            'tr[data-id]',
            '.bulletin-list tr',
            '.list-item'
        ]
        
        rows = []
        for selector in possible_selectors:
            rows = soup.select(selector)
            if rows:
                print(f"✓ 게시글 목록 발견: {selector} ({len(rows)}개)")
                break
        
        if not rows:
            print("⚠️ 게시글 목록을 찾을 수 없습니다.")
            print("HTML 구조 분석 필요:")
            print(html[:500])
            return []
        
        for row in rows:
            try:
                # 분류 찾기
                category_elem = row.select_one('.category, .classification, td:nth-child(1), .type')
                category = category_elem.text.strip() if category_elem else ''
                
                # '아르바이트' 분류만 필터링
                if '아르바이트' not in category:
                    continue
                
                # 제목
                title_elem = row.select_one('.title, .subject, td.title, a.title')
                title = title_elem.text.strip() if title_elem else '제목 없음'
                
                # 링크/ID
                link_elem = row.select_one('a[href]')
                href = link_elem.get('href', '') if link_elem else ''
                post_id = href.split('=')[-1] if '=' in href else ''
                
                # 작성자
                author_elem = row.select_one('.author, .writer, td.author')
                author = author_elem.text.strip() if author_elem else '익명'
                
                # 날짜
                date_elem = row.select_one('.date, .regdate, td.date')
                date = date_elem.text.strip() if date_elem else ''
                
                job_posts.append({
                    'id': post_id,
                    'title': title,
                    'author': author,
                    'date': date,
                    'category': category,
                    'url': f"{self.base_url}{href}" if href and not href.startswith('http') else href
                })
                
                print(f"  ✓ 발견: [{category}] {title}")
                
            except Exception as e:
                print(f"⚠️ 게시글 파싱 오류: {e}")
                continue
        
        return job_posts
    
    def send_telegram_message(self, post):
        """텔레그램으로 알림 전송"""
        title = post.get('title', '제목 없음')
        author = post.get('author', '익명')
        date = post.get('date', '')
        category = post.get('category', '')
        post_id = post.get('id', '')
        
        # URL 생성
        url = post.get('url', f"{self.board_url}&a={post_id}")
        
        message = f"""🔔 새로운 아르바이트 공고!

🏷️ 분류: {category}
📌 제목: {title}
👤 작성자: {author}
📅 날짜: {date}

🔗 {url}
"""
        
        try:
            api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": True
            }
            response = requests.post(api_url, json=payload, timeout=10)
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
            # ID가 없으면 제목으로 중복 체크
            identifier = post_id if post_id else post.get('title', '')
            
            if identifier and identifier not in self.seen_posts:
                new_posts.append(post)
                self.seen_posts.add(identifier)
        
        # 새 게시글 알림
        for post in new_posts:
            self.send_telegram_message(post)
            time.sleep(2)
        
        if new_posts:
            self.save_seen_posts()
        
        return len(new_posts)
    
    def run(self):
        """메인 루프"""
        print("=" * 60)
        print("🚀 한국기술교육대학교 아르바이트 알림 봇 시작!")
        print(f"📋 게시판: 학생생활 (b=21)")
        print(f"🏷️  필터: 분류='아르바이트'")
        print(f"⏰ 체크 주기: {CHECK_INTERVAL}초 ({CHECK_INTERVAL//60}분)")
        print("=" * 60)
        
        # 시작 알림
        try:
            start_message = "🤖 아르바이트 알림 봇이 시작되었습니다!\n\n📋 학생생활 게시판\n🏷️ 분류: 아르바이트"
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
                    print("💤 새 아르바이트 공고 없음")
                
                print(f"⏰ {CHECK_INTERVAL}초 후 다시 확인...")
                time.sleep(CHECK_INTERVAL)
            
            except KeyboardInterrupt:
                print("\n👋 프로그램 종료")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                print("⏰ 60초 후 재시도...")
                time.sleep(60)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 오류: TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정해주세요!")
        exit(1)
    
    notifier = KoreatechJobNotifier()
    notifier.run()
