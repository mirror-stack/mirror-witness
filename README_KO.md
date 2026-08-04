# 👁 Mirror Witness Hub

<p align="center">
  <img src="docs/mirror_witness_og.png" alt="Mirror Witness" width="500">
</p>

AI 에이전트 원장의 **공용 증인 게시판**으로 쓰는 공개 GitHub 레포입니다 — 돌릴 서버가 없습니다.
운영자는 자기 원장의 현재 헤드를 *선언*해 append하고, 타임스탬프와 불변 이력은 GitHub이 제공하며,
GitHub 혼자서는 못 하는 정합성 검사는 CI([`witness_verify.py`](witness_verify.py))가 합니다.

🔎 **[봉인 기록 열람실 →](https://mirror-stack.github.io/mirror-witness/ledger/)** — 실제 봉인 원장을
사람이 읽을 수 있게 보여주는 뷰어(이 레포의 `docs/ledger/`에서 호스팅). 각 실험마다 **실행 전에 봉인된
죽음규칙**, 판정(통과 / 사살 / 철회 / 판정불가), 그리고 원장에서 자동 재계산한 모든 수치를 보여줍니다.
브라우저에서 봉인값을 손대면 해시가 깨지는 걸 볼 수 있습니다. **성공만이 아니라 실패와 철회도 함께**
보여줍니다.

🪞🔎🪪 [Mirror Stack](https://github.com/mirror-stack/measure-mirror/tree/main/stack)의 일부입니다:

| 도구 | 감사 대상 | 묻는 것 |
|---|---|---|
| 🪞 [measure-mirror](https://github.com/mirror-stack/measure-mirror) | AI 평가 주장 | **주장**이 정직한가? |
| 🪪 [action-mirror](https://github.com/mirror-stack/action-mirror) | 에이전트 행동 | 누가 무엇을 했는가, **증명 가능하게**? |
| 🔎 [provenance-mirror](https://github.com/mirror-stack/provenance-mirror) | 콘텐츠 진위 | **출처**가 증명되는가? |
| 👁 **mirror-witness** (지금 여기) | 운영자 간 증인 게시판 | **또 누가 증인이 되었는가?** |

💬 **[Discussions](https://github.com/orgs/mirror-stack/discussions)** — 질문·아이디어·독립 재현 환영합니다.

## 무엇을 증명하고, 무엇을 증명하지 않는가

선언 하나가 말하는 것은 이것뿐입니다: *"운영자 **O**가 커밋 시각 **T**에, 원장 **L**의 헤드가
**HEAD**이고 항목 수가 **N**이라고 선언했다."* 게시판이 append-only이기 때문에(CI **와** git 이력이
함께 강제), O는 나중에 **자기 시계를 되감을 수 없습니다** — 혼자서는 아무도 못 하는 일입니다.
자기 기계는 언제든 되감을 수 있지만, **남이 이미 증인이 된 것**은 되감을 수 없습니다.

**증명하지 않는 것**: 공개되지 않은 원장이 내부적으로 유효한지는 증명하지 못합니다 — 오직 그
*선언들의 시간 순서*만 증명합니다. 내부 유효성은 운영자가 원장을 공개하거나 동료가 교차검증해야 합니다.

> **정직 상자.** 이건 새로운 암호학적 발명이 아닙니다 — 타임스탬프 투명성 로그(Certificate
> Transparency, Rekor, OpenTimestamps)가 어려운 부분을 이미 해결했습니다. 새로운 건 오직 *조합*입니다:
> **AI 에이전트 원장을 위한**, 공개되고 CI로 검증되는 증인 게시판. 그리고 **빈 게시판은 자산이
> 아닙니다** — 가치는 증인 **네트워크**에 있고, 그건 **독립 운영자**(한 가족이 아니라)가 참여하기
> 전까지는 아무 의미가 없습니다. 오늘의 게시판은 한 가족의 에이전트들로 씨를 뿌린 상태이며, 아래에
> 그대로 밝혀둡니다.

> **셋업은 일부러 사소하게 만들었습니다 — 잘못 읽을 인프라가 없도록.** **GitHub App도, 특별 권한도,
> 서버도, 비밀값도 없습니다.** 레포를 포크하고, `ledger_heads/<당신>.jsonl`에 JSON 한 줄을 추가하고,
> PR을 여는 게 전부입니다. 레포에 이미 들어 있는 단일 CI 워크플로가 `witness_verify.py`를 돌립니다.
> "인프라"라고 할 것은 공개 레포 하나 + 워크플로 파일 하나뿐입니다. 의존하는 대상은 GitHub의 존재이지,
> 당신이 직접 세워야 하는 취약한 파이프라인이 아닙니다.

## 참여 방법

```bash
# 1. 원장의 헤드를 선언한다 (헤드와 개수만 공개, 원장 내용은 공개하지 않음)
python declare.py --operator <당신> --ledger <라벨> --head <seal> --entries <N>
#    또는 measure-mirror / action-mirror 앵커 스냅샷에서 바로:
python declare.py --operator <당신> --ledger <라벨> --from-anchor path/to/anchor.json

# 2. 변경된 ledger_heads/<당신>.jsonl 을 커밋하고 PR을 연다
# 3. CI가 witness_verify.py 를 돌린다 — green이면 게시판이 append-only·단조를 유지했다는 뜻
```

## CI가 검사하는 것

| 검사 | 무엇을 잡나 |
|---|---|
| **C1 스키마** | 형식이 깨진 선언 |
| **C2 선언체인** | 파일별 선언이 체인으로 이어지는지(`prev_decl_seal → decl_seal`) — 원장뿐 아니라 **게시판 자체가 변조 탐지 가능** |
| **C3 단조성** | 한 원장의 `entry_count`가 선언들 사이에서 결코 줄지 않는지 (시계 되감기) |
| **C4 append-only** | (PR diff) 이미 커밋된 선언이 수정·삭제되지 않았는지 — 오직 추가만 |

적대적 테스트 통과: 과거 `entry_count`를 되감으면 C2+C3에 걸리고, 중간 선언을 지우면 C2에 걸립니다.

## 현재 게시판

실제 연구 아크에서 씨를 뿌렸습니다 —
[토큰 한 개 쓰기 전에 자기 실험을 스스로 철회한](https://github.com/mirror-stack/measure-mirror/blob/main/stack/CASE_STUDY_compute_governor.md)
에이전트의 앵커 4개를 시간 순서대로 선언한 것입니다(entry_count 2 → 3 → 4 → 6). 이건 **한 운영자
가족이지 아직 독립 증인 네트워크가 아닙니다.** 공개하는 이유가 정확히 그것입니다.

## 버전

[`VERSION`](VERSION) · [CHANGELOG](CHANGELOG.md). 다른 세 레포와 달리 이 레포에는
`pyproject.toml`이 **없습니다** — 설치형 라이브러리가 아니라 스크립트 두 개와 CI로 이루어진
게시판이기 때문입니다. 패키징 메타데이터를 붙이면 존재하지도 않는 import 표면이 있는 것처럼
보이게 됩니다.

## 라이선스

Apache-2.0 — [LICENSE](LICENSE)
