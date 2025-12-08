[주간 보고서 작성 지침]

## 목적
- Confluence 페이지와 JIRA 티켓을 읽고 CTO에게 보고할 주간 업무 보고서를 작성합니다.

## 작성 원칙
- Confluence 페이지에 언급된 모든 JIRA 티켓을 빠짐없이 나열합니다. (JIRA 티켓의 상세 내용을 읽을 필요는 없습니다.)
- **JIRA 티켓 링크 형식**: 반드시 `[TICKET-ID](URL) 설명` 형식의 마크다운 링크로 작성합니다.
  - 예시: `[VITALCARES-4170](https://aitrics.atlassian.net/browse/VITALCARES-4170) outliers 컬럼 추가`
  - 예시: `[ER-1607](https://aitrics.atlassian.net/browse/ER-1607) 환자 내원일시 변경 시 알람 미삭제 수정`
- **간결하게 작성**: 설명은 핵심만 20자 이내로 작성합니다.
- **prefix 제거**: 티켓 제목의 `[VCBE]`, `[VC]`, `[ER]` 같은 prefix는 제거합니다.

## 제품 및 Component 기반 그룹핑
- JIRA 티켓의 Details > Components 필드를 확인하여 작업 내용을 분류합니다.
- Component명의 prefix로 제품을 구분합니다:
  - `vc-` prefix: VC 제품
  - `er-` prefix: ER 제품
- 반드시 제품별(VC/ER)로 먼저 구분한 후, 각 제품 내에서 진행 상태별, Component별로 그룹핑합니다.
- 같은 Component에 해당하는 작업들은 하나의 그룹으로 묶어서 표현합니다.

## 보고서 형식
```
VC

[진행 완료]
- {Component명}
  - 완료된 작업 항목

[진행 중]
- {Component명}
  - 진행 중인 작업 항목

[진행 대기]
- 특이사항 없음

ER

[진행 완료]
- {Component명}
  - 완료된 작업 항목

[진행 중]
- {Component명}
  - 진행 중인 작업 항목

[진행 대기]
- 특이사항 없음
```

## 작성 시 주의사항
- **누락 금지**: Confluence 페이지에 언급된 모든 티켓과 Component를 빠짐없이 포함합니다. (vc-scoring-manager, vc-sync 등 모든 Component 포함)
- 제품(VC/ER)을 반드시 분리하여 작성합니다. 절대 섞이면 안 됩니다.
- 같은 Component의 작업은 반드시 하나로 묶어서 표현합니다.