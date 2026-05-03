# Pluck — Quick Start (당신이 지금 해야 할 것)

## 5분 안에 배포 시작하기

### 당신이 지금 터미널에서 해야 할 것

```bash
# 1️⃣ 프로젝트 디렉토리로 이동
cd ~/Desktop/shopping-extractor

# 2️⃣ Git 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 3️⃣ Git 초기화 및 커밋
git init
git add .
git commit -m "Initial commit: Pluck — AI shopping extractor"
git branch -M main

# 4️⃣ GitHub에서 저장소 생성 후 URL 복사
# 1. https://github.com/new 방문
# 2. Repository name: pluck
# 3. Public 선택
# 4. "Create repository" 클릭
# 5. 나오는 URL을 복사 (예: https://github.com/YOUR_USERNAME/pluck.git)

# 5️⃣ 원격 저장소 추가 및 푸시 (위에서 복사한 URL을 붙여넣기)
git remote add origin https://github.com/YOUR_USERNAME/pluck.git
git push -u origin main
```

---

## 다음: Product Hunt 런칭 (2시간)

### Step 1️⃣ GUI 테스트 + 스크린샷

```bash
# GUI 실행
.venv/bin/python main.py --gui

# 다음 4개의 스크린샷을 촬영하세요:
# 1. 메인 화면 (URL 입력칸 보이는 상태)
# 2. AI 엔진 선택 드롭다운 (Local/Claude/OpenAI/Gemini/Ollama)
# 3. 추출 결과 (제품 카드 그리드)
# 4. 구독 플랜 다이얼로그
```

### Step 2️⃣ Product Hunt 계정 생성

1. https://producthunt.com 접속
2. "Sign up" → Google 또는 이메일로 가입
3. 이메일 인증 완료

### Step 3️⃣ Product Hunt에 제출

1. https://producthunt.com/products/new 접속
2. 아래 정보 입력:

```
제품명: Pluck

한 줄 요약: 
AI-powered shopping extractor — no API key needed for local mode

설명:
Extract product names, prices, discount rates & images from any e-commerce site in seconds.

Features:
• Local mode (free) — PaddleOCR runs entirely on your device
• Cloud mode (optional) — Claude, GPT-4o, Gemini, or Ollama
• Modern dark GUI — inspired by Linear & Raycast
• Custom extraction — "extract size, color, material" via LLM instructions
• Subscription system — Free / Pro / Team tiers

Works on macOS, Windows, Linux.

카테고리:
- Productivity
- Developer Tools

웹사이트:
https://github.com/YOUR_USERNAME/pluck

가격:
Free (+ Pro / Team tiers)

스크린샷:
위에서 촬영한 4개 스크린샷 업로드
```

### Step 4️⃣ 런칭 날짜 설정

- "Launch on [내일 날짜]" 클릭
- 또는 즉시 런칭하려면 "Coming Soon" → "Live" 전환

---

## 동시에 준비할 것 (선택사항)

### Discord 커뮤니티 (5분)

```bash
# 1. https://discord.new 접속
# 2. "Create My Own" 클릭
# 3. 서버 이름: "Pluck Community"
# 4. Settings → Invites → 초대 링크 복사
# 5. GitHub README.md의 "Feedback & Support" 섹션에 링크 추가
```

---

## 체크리스트

당신이 해야 할 것:

- [ ] Git config 설정 (Step 1)
- [ ] GitHub 저장소 생성 (https://github.com/new)
- [ ] 로컬에서 git push (위의 Step 5)
- [ ] GUI 스크린샷 4개 촬영
- [ ] Product Hunt 계정 생성
- [ ] Product Hunt에 제품 정보 입력
- [ ] 런칭!

---

## 성공 신호

- ✅ GitHub에 코드가 업로드됨 (https://github.com/YOUR_USERNAME/pluck)
- ✅ Product Hunt에 라이브 됨
- ✅ 첫 번째 피드백/댓글이 옴

---

## 문제 해결

**"git remote add origin" 실패?**
```bash
# 이미 remote가 있는 경우:
git remote remove origin
git remote add origin YOUR_URL
git push -u origin main
```

**"git push" 실패?**
```bash
# SSH 키 생성 필요:
ssh-keygen -t ed25519 -C "your.email@example.com"
# GitHub Settings → SSH Keys에 public key 추가
```

---

**준비됐나요? 시작합시다! 🚀**
