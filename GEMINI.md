[주간 보고서 작성 지침]

## 목적
- Confluence 페이지와 JIRA 티켓을 읽고 CTO에게 보고할 주간 업무 보고서를 작성합니다.

## 작성 원칙
- Confluence 페이지에 언급된 모든 JIRA 티켓을 빠짐없이 포함합니다.
- **JIRA 티켓 상세 내용 확인 필수**: 각 티켓의 제목과 설명을 읽고, 관련 있는 티켓들을 주제별로 묶습니다.
- **prefix 제거**: 티켓 제목의 `[VCBE]`, `[VC]`, `[ER]`, `[on-call]` 같은 prefix는 제거합니다.

## 주제별 그룹핑 (핵심)
- **관련 티켓 통합**: 동일한 기능/이슈에 대한 여러 티켓은 하나의 주제로 묶어서 표현합니다.
  - 예: UTC 변환 관련 티켓 3개 → "UTC 시간 변환 처리"로 통합
  - 예: Hb, pO2, pCO2 추가 관련 티켓 → "Hb, pO2, pCO2 파라미터 추가"로 통합
- **주제 도출 기준**: 티켓 제목과 설명에서 공통 키워드, 동일 기능, 연관된 버그/개선사항을 파악합니다.

## 제품 및 Component 기반 구조
- JIRA 티켓의 Details > Components 필드를 확인하여 작업 내용을 분류합니다.
- Component명의 prefix로 제품을 구분합니다:
  - `vc-` prefix: VC 제품
  - `er-` prefix: ER 제품
- 반드시 제품별(VC/ER)로 먼저 구분한 후, 각 제품 내에서 진행 상태별, Component별로 그룹핑합니다.

## 보고서 출력 형식

### 메인 메시지 (간결하게)
```
VC

[진행 완료]
- {Component명}
  - 주제 설명

[진행 중]
- {Component명}
  - 주제 설명

[진행 대기]
- 특이사항 없음

ER

[진행 완료]
- {Component명}
  - 주제 설명

[진행 중]
- {Component명}
  - 주제 설명

[진행 대기]
- 특이사항 없음
```

### Thread 메시지 (상세 티켓 목록)
각 주제에 대해 Slack Thread로 관련 티켓들을 나열합니다.
```
[주제명] 관련 티켓:
- [TICKET-1](URL) 티켓 제목
- [TICKET-2](URL) 티켓 제목
```

## 예시

**메인 메시지:**
```
- vc-sync
  - UTC 시간 변환 처리
  - sync restore 날짜 지정 개선
```

**Thread (UTC 시간 변환 처리):**
```
[UTC 시간 변환 처리] 관련 티켓:
- [VITALCARES-4329](https://aitrics.atlassian.net/browse/VITALCARES-4329) vc_observation 테이블 시간 처리 방식 문의
- [VITALCARES-4331](https://aitrics.atlassian.net/browse/VITALCARES-4331) vital 데이터 emr_created_dt UTC 미변환 현상
- [VITALCARES-4332](https://aitrics.atlassian.net/browse/VITALCARES-4332) vitalsign emr_created_dt UTC 변환 수정
```

## JSON 출력 형식
메인 메시지와 Thread 데이터를 구분하기 위해 다음 JSON 형식으로 출력합니다:
```json
{
  "main": "메인 메시지 내용",
  "threads": [
    {
      "topic": "주제명",
      "tickets": [
        {"id": "TICKET-ID", "url": "URL", "title": "티켓 제목"}
      ]
    }
  ]
}
```

## 작성 시 주의사항
- **누락 금지**: Confluence 페이지에 언급된 모든 티켓을 빠짐없이 포함합니다.
- **주제 통합 필수**: 관련 있는 티켓들은 반드시 하나의 주제로 묶어서 간결하게 표현합니다.
- 제품(VC/ER)을 반드시 분리하여 작성합니다. 절대 섞이면 안 됩니다.
- 같은 Component의 작업은 반드시 하나로 묶어서 표현합니다.
- 단독 티켓도 주제로 표현합니다 (Thread에는 해당 티켓 1개만 나열).