# /commit - Complete and Push Changes

작업을 마무리하고 변경사항을 커밋 및 푸시합니다.

## Usage

```
/commit              # 현재 세션의 모든 변경사항을 커밋 및 푸시
/commit [message]    # 커스텀 메시지로 커밋 및 푸시
```

## Workflow

작업 마무리 시 다음 단계를 자동으로 수행합니다:

1. **Pre-commit Check**: wrap up 필요 여부 확인
2. **Status Check**: 변경된 파일 확인
3. **Commit Message**: Conventional Commits 규칙에 따라 메시지 생성
4. **Commit**: 변경사항 스테이징 및 커밋
5. **Push**: 원격 저장소로 푸시
6. **Report**: 결과 보고

## Steps

### Step 1: Pre-commit Check

커밋 전 문서 동기화 상태를 확인합니다.

#### 감지 로직

```bash
git status
```

**판단 기준:**

| src/ 변경 | docs 변경 | 결과 |
|-----------|-----------|------|
| O | X | ⚠️ `/wrap`을 먼저 실행하세요 |
| O | O | 정상 진행 |
| X | O | 정상 진행 |
| X | X | 변경사항이 없습니다 |

- **src/ 변경**: `src/` 디렉토리 하위 파일의 변경 여부
- **docs 변경**: `README.md` 또는 `CLAUDE.md` 파일의 변경 여부

#### 경고 발생 시

소스 코드 변경이 있지만 문서가 업데이트되지 않은 경우:

```
⚠️ 소스 코드가 변경되었지만 문서가 업데이트되지 않았습니다.
   /wrap을 먼저 실행하여 문서를 동기화하세요.

   변경된 소스 파일:
   - src/domain/models.py
   - src/application/use_cases.py
```

사용자에게 `/wrap` 실행을 권장하고, 커밋을 계속할지 확인합니다.

### Step 2: Check Status

변경된 파일을 확인합니다.

```bash
git status
git diff HEAD
```

### Step 3: Generate Commit Message

Conventional Commits 규칙에 따라 커밋 메시지를 생성합니다.

**Format:**
```
<type>(<scope>): <subject>

[optional body]

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 의존성 등

**Scopes:**
- `domain`: 도메인 레이어
- `app`: 애플리케이션 레이어
- `infra`: 인프라스트럭처 레이어
- `docs`: 문서
- `config`: 설정

### Step 4: Commit

변경사항을 스테이징하고 커밋합니다.

```bash
# 파일별로 스테이징 (git add . 보다 권장)
git add <specific-files>

# HEREDOC을 사용한 커밋 (포맷팅 보장)
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 5: Push

원격 저장소로 푸시합니다.

```bash
git push

# 새 브랜치의 경우
git push -u origin <branch-name>
```

### Step 6: Report

사용자에게 결과를 보고합니다.

```
Commit: <type>(<scope>): <subject>
Branch: <branch-name>
Files Changed: N files (+X, -Y)

Summary:
- 문서 업데이트 완료
- N files committed
- Pushed to origin/<branch-name>
```

## Edge Cases

### No Changes to Commit

변경사항이 없는 경우 커밋하지 않습니다.

### Push Conflict

```bash
# 푸시 충돌 시 사용자에게 안내
git pull --rebase
git push
```

### Documentation Not Updated

소스 코드 변경 시 문서 동기화가 필요합니다. Pre-commit Check에서 경고가 발생하면 `/wrap`을 먼저 실행하세요.

## Example Session

### 정상 케이스

```
User: /commit

Claude:
1. [Pre-commit Check] ✅ 문서 동기화 상태 양호
2. [Status] 3 files changed
3. [Commit] feat(domain): add new report model
4. [Push] origin/main
5. [Report] 완료
```

### 경고 케이스

```
User: /commit

Claude:
1. [Pre-commit Check]
   ⚠️ 소스 코드가 변경되었지만 문서가 업데이트되지 않았습니다.

   변경된 소스 파일:
   - src/domain/models.py

   /wrap을 먼저 실행하시겠습니까? (권장)

User: yes

Claude:
[/wrap 실행 후 다시 /commit 진행]
```
