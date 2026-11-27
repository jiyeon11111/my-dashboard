import streamlit as st  # 웹 화면을 만드는 라이브러리
import pandas as pd  # 표 형태 데이터를 다루는 라이브러리

# 페이지 설정: 화면을 넓게 쓰고, 브라우저 탭 제목을 정한다
st.set_page_config(page_title="LightNow 대외활동 공고 현황", layout="wide")

# 제목과 캡션(제목 아래 작은 설명 글)
st.title("LightNow 대외활동 공고 현황")
st.caption("데이터 기준: 2026년 11월~2027년 3월 마감 공고")
# 대시보드의 목적을 알려 주는 설명 글
# :small[...] → 작은 글씨지만 기본 글자색이라 회색 캡션보다 진하게 보인다
st.markdown(
    ":small[LightNow 운영자가 활동 유형, 마감일, 활동 기간에 따라 공고 현황을 파악하고, "
    "공고 수집 및 추천 서비스의 운영 방향을 결정할 수 있는 대시보드이다.]"
)

DATA_FILE = "activities.csv"  # 읽어 올 파일 이름
REQUIRED_COLUMNS = ["id", "name", "category", "recruits", "weeks", "deadline"]  # 꼭 있어야 하는 열


# 데이터 불러오기 함수
# @st.cache_data: 한 번 읽은 결과를 기억해 두고, 조건을 바꿔도 파일을 다시 읽지 않는다
@st.cache_data
def load_data():
    # 날짜 변환은 아래에서 따로 한다 (deadline 열이 없을 때 여기서 에러가 나지 않도록)
    return pd.read_csv(DATA_FILE)


# ── 안전장치 1: 파일이 없거나 읽을 수 없을 때 ──
try:
    df = load_data()
except FileNotFoundError:
    st.error(
        f"'{DATA_FILE}' 파일을 찾을 수 없습니다. "
        "파일 이름이 정확한지, app.py와 같은 폴더에 있는지 확인한 뒤 새로고침해 주세요."
    )
    st.stop()  # 여기서 화면 그리기를 멈춘다
except pd.errors.EmptyDataError:
    st.error(f"'{DATA_FILE}' 파일이 비어 있습니다. 파일에 데이터가 들어 있는지 확인한 뒤 새로고침해 주세요.")
    st.stop()
except Exception as e:  # 그 밖에 파일을 읽다가 생긴 문제 (형식·인코딩 등)
    st.error(f"'{DATA_FILE}' 파일을 읽지 못했습니다 ({e}). CSV 형식으로 저장되어 있는지 확인해 주세요.")
    st.stop()

# ── 안전장치 2: 필요한 열이 빠져 있을 때 ──
missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]  # 없는 열만 골라낸다
if missing:
    st.error(
        f"'{DATA_FILE}'에 필요한 열이 없습니다: {', '.join(missing)}. "
        "첫 줄(열 이름)에 이 열을 추가하거나 철자를 확인한 뒤 새로고침해 주세요."
    )
    st.stop()

# ── 안전장치 3: 값이 잘못 들어간 줄 정리 ──
df = df.copy()  # 캐시에 저장된 원본은 건드리지 않도록 복사본을 쓴다
# errors="coerce": 날짜·숫자로 바꿀 수 없는 값은 빈칸(NaN)으로 만든다 (에러 대신)
df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce")
df["recruits"] = pd.to_numeric(df["recruits"], errors="coerce")
df["weeks"] = pd.to_numeric(df["weeks"], errors="coerce")
before = len(df)
df = df.dropna(subset=["category", "recruits", "weeks", "deadline"])  # 빈칸이 있는 줄은 뺀다
df["category"] = df["category"].astype(str)  # 유형은 글자로 통일
if len(df) < before:
    st.warning(
        f"값이 비었거나 형식이 맞지 않는 {before - len(df)}건은 제외했습니다. "
        "모두 보려면 파일에서 해당 줄의 날짜·숫자를 고쳐 주세요."
    )
if df.empty:
    st.error(f"'{DATA_FILE}'에 사용할 수 있는 공고가 없습니다. 파일 내용을 확인한 뒤 새로고침해 주세요.")
    st.stop()

# ── 왼쪽 사이드바: 조건(필터) 선택 ──
st.sidebar.header("조건 선택")

min_date = df["deadline"].min().date()  # 데이터에서 가장 이른 마감일 (.date()로 날짜만 남김)
max_date = df["deadline"].max().date()  # 데이터에서 가장 늦은 마감일
today = pd.Timestamp.today().normalize()  # 기준일: 오늘 (시각은 0시로 맞춤)


# 빠른 선택 버튼 이름 → (시작일, 종료일)로 바꿔 주는 함수
def quick_range(choice):
    if choice == "이번 주":
        # 오늘 ~ 이번 주 일요일 (weekday(): 월=0 … 일=6)
        week_end = today + pd.Timedelta(days=6 - today.weekday())
        return (today.date(), week_end.date())
    if choice == "2주 이내":
        return (today.date(), (today + pd.Timedelta(days=14)).date())  # 오늘 ~ 14일 뒤
    if choice == "이번 달":
        month_end = today + pd.offsets.MonthEnd(0)  # 이번 달 마지막 날
        return (today.date(), month_end.date())
    return (min_date, max_date)  # '전체': 데이터의 처음 ~ 끝


# 빠른 선택 버튼을 누르면 실행: 달력 기간을 버튼에 맞게 바꿔 준다
def on_quick_change():
    # .get(): 값이 없어도 에러 대신 None을 돌려준다 (KeyError 방지)
    choice = st.session_state.get("quick")
    if choice is not None:  # 버튼을 다시 눌러 선택을 끈 경우(None)는 그대로 둔다
        st.session_state["date_range"] = quick_range(choice)


# 달력을 직접 바꾸면 실행: 빠른 선택 버튼의 표시를 꺼서 헷갈리지 않게 한다
def on_date_change():
    st.session_state["quick"] = None


# 값이 없을 때만 기본값을 정해 둔다 (session_state: 새로고침 전까지 값을 기억하는 저장소)
# 두 값을 따로따로 검사해서, 하나만 사라진 경우에도 다시 채워 넣는다
if "quick" not in st.session_state:
    st.session_state["quick"] = "전체"
if "date_range" not in st.session_state:
    st.session_state["date_range"] = quick_range(st.session_state["quick"])

# 1) 마감 빠른 선택 버튼
st.sidebar.segmented_control(
    "마감 빠른 선택",
    options=["이번 주", "2주 이내", "이번 달", "전체"],
    key="quick",  # 값을 st.session_state["quick"]에 저장
    on_change=on_quick_change,
)

# 2) 마감일 달력: 시작일~종료일 두 날짜를 고른다 (값은 session_state["date_range"]에 저장)
date_range = st.sidebar.date_input(
    "마감일 기간", key="date_range", on_change=on_date_change, format="YYYY-MM-DD"
)

# 날짜 하나만 돌려받은 경우에도 아래 코드가 똑같이 돌도록 묶음(튜플)으로 맞춘다
if not isinstance(date_range, (tuple, list)):
    date_range = (date_range,)

# 시작일만 고르고 종료일을 아직 안 골랐을 때도 에러가 나지 않게 처리
if len(date_range) == 2:  # 두 날짜를 다 고른 경우
    start_date, end_date = date_range
elif len(date_range) == 1 and date_range[0] is not None:  # 시작일만 고른 경우 → 종료일은 데이터의 마지막 날로
    start_date, end_date = date_range[0], max_date
else:  # 달력을 비운 경우 → 전체 기간
    start_date, end_date = min_date, max_date

# 3) 활동 유형: 버튼형 여러 개 선택, 처음에는 전체 선택
all_categories = sorted(df["category"].unique())  # 데이터에 있는 유형 목록(알파벳 순)
# 화면에 보일 한글 이름 (사이드바 버튼과 그래프에서 같이 쓴다)
korean_names = {"contest": "공모전", "supporters": "서포터즈", "volunteer": "봉사활동"}
# 활동 유형별 색 (사이드바 버튼 글자와 막대 그래프에 같이 쓴다)
# - 버튼 글자: Streamlit 글자색 이름 (:blue[...] 처럼 씀)
# - 막대: 같은 계열의 실제 색 코드 (Streamlit 기본 테마의 파랑·주황·초록)
color_names = {"contest": "blue", "supporters": "orange", "volunteer": "green"}
color_codes = {"contest": "#3B82F6", "supporters": "#E0682B", "volunteer": "#079464"}
OTHER_COLOR_NAME, OTHER_COLOR_CODE = "gray", "#9CA3AF"  # 목록에 없는 새 유형은 회색


# 버튼에 보일 글자 만들기: 'contest' → ':blue[공모전]' (파란 글자 '공모전'으로 보임)
def pill_label(category):
    name = korean_names.get(category, category)  # 한글 이름 (없으면 원래 이름)
    color = color_names.get(category, OTHER_COLOR_NAME)
    return f":{color}[{name}]"


selected_categories = st.sidebar.pills(
    "활동 유형",
    options=all_categories,  # 실제 값은 영어 그대로 (필터에 그대로 쓰임)
    selection_mode="multi",
    default=all_categories,
    format_func=pill_label,  # 버튼에 보이는 글자만 한글 + 색으로 바꾼다
)

# 4) 활동 기간: 단기/중기/장기 중 범위를 고른다
week_options = ["단기(1~4주)", "중기(5~12주)", "장기(13주 이상)"]
week_start_label, week_end_label = st.sidebar.select_slider(
    "활동 기간", options=week_options, value=(week_options[0], week_options[-1])
)
# 고른 구간 이름을 실제 주 수로 바꾼다 (시작 구간의 최소 주 ~ 끝 구간의 최대 주)
week_min = {"단기(1~4주)": 1, "중기(5~12주)": 5, "장기(13주 이상)": 13}
week_max = {"단기(1~4주)": 4, "중기(5~12주)": 12, "장기(13주 이상)": max(13, int(df["weeks"].max()))}
week_from = week_min[week_start_label]
week_to = week_max[week_end_label]

# ── 조건으로 데이터 거르기 → filtered ──
# 세 조건을 모두 만족하는 줄만 남긴다 (&는 '그리고')
filtered = df[
    df["category"].isin(selected_categories)  # 고른 유형에 속하는지
    & df["deadline"].dt.date.between(start_date, end_date)  # 마감일이 기간 안인지
    & df["weeks"].between(week_from, week_to)  # 활동 기간이 범위 안인지
]

# 필터 아래에 몇 건이 남았는지 표시
st.sidebar.write(f"선택 조건: {len(filtered)}건 / 전체 {len(df)}건")

# ── 안전장치 4: 조건에 맞는 공고가 0건일 때 (탭을 그리기 전에 검사) ──
if filtered.empty:
    st.info("선택한 조건에 맞는 공고가 없습니다. 왼쪽 사이드바에서 기간을 넓히거나 활동 유형을 더 골라 주세요.")
    st.stop()  # 요약·상세 탭 모두 그리지 않고 멈춘다

# 본문 탭 두 개 만들기
tab_summary, tab_detail = st.tabs(["요약", "상세 데이터"])

with tab_summary:
    # 핵심 숫자 3개를 가로로 나란히 보여 주기 위해 칸(열) 3개를 만든다
    col1, col2, col3 = st.columns(3)

    # 공고 수: 행(줄) 개수 = 공고 개수
    col1.metric("공고 수", f"{len(filtered)}건")

    # 총 모집 인원: recruits 열을 모두 더하고, {:,}로 천 단위 쉼표를 붙인다
    col2.metric("총 모집 인원", f"{int(filtered['recruits'].sum()):,}명")

    # 평균 활동 기간: weeks 열의 평균, {:.1f}로 소수점 한 자리까지 표시
    col3.metric("평균 활동 기간", f"{filtered['weeks'].mean():.1f}주")

    # 그래프 두 개를 좌우로 나란히 놓기 위해 칸 2개를 만든다
    left, right = st.columns(2)

    # 두 그래프에 같이 쓰는 글자 모양
    TEXT_COLOR = "#31333F"  # Streamlit 본문 글자와 같은 진한 회색 (기본 축 글자는 연한 회색)
    AXIS_LABEL = {"labelFontSize": 14, "labelFontWeight": "bold", "labelColor": TEXT_COLOR}  # 축 글자: 크게·굵게·진하게
    NUMBER_TEXT = {"type": "text", "fontSize": 14, "fontWeight": "bold", "color": TEXT_COLOR}  # 그래프 위 숫자 모양

    # ── 왼쪽: 월별 마감 공고 수 (선 그래프) ──
    with left:
        st.subheader("월별 마감 공고 수")
        # to_period("M"): 날짜를 '2026-11' 같은 월 단위로 바꾼다 → 월마다 개수를 세고 시간 순으로 정렬
        monthly = filtered["deadline"].dt.to_period("M").value_counts().sort_index()
        monthly = monthly.rename_axis("마감 월").reset_index(name="공고 수")  # 표 형태로 정리
        # 화면용 이름 만들기: 2026-11 → '26년 11월' (year % 100: 연도의 뒤 두 자리)
        labels = [f"{p.year % 100}년 {p.month}월" for p in monthly["마감 월"]]
        monthly["마감 월"] = labels
        # 점 위 숫자가 그래프 위쪽에서 잘리지 않도록 y축 최댓값을 가장 큰 값보다 25% 넉넉하게 잡는다
        y_top = int(monthly["공고 수"].max() * 1.25) + 1
        # vega_lite_chart: 그래프 모양을 사전(dict)으로 하나하나 정해 주는 방식
        st.vega_lite_chart(
            monthly,
            {
                "height": 300,  # 그래프 높이
                # encoding: 아래 layer(겹쳐 그리는 그림)들이 같이 쓰는 x·y 설정
                "encoding": {
                    "x": {
                        "field": "마감 월",
                        "type": "ordinal",  # 순서가 있는 글자 값
                        # sort에 목록을 직접 주면 그 순서대로 그린다
                        # (가나다순이면 '26년 10월'이 '26년 9월'보다 앞에 오므로 시간 순 목록을 넘긴다)
                        "sort": labels,
                        "title": None,  # 축 이름 숨김 (소제목과 겹치므로)
                        "axis": {"labelAngle": 0, **AXIS_LABEL},  # 글자 가로 + 크게·굵게·진하게
                    },
                    "y": {
                        "field": "공고 수",
                        "type": "quantitative",  # 숫자 값
                        "title": None,
                        "scale": {"domain": [0, y_top]},  # 0부터 y_top까지
                        "axis": {"tickMinStep": 1, **AXIS_LABEL},  # 눈금을 1 단위로 (0.5건 같은 눈금 방지)
                    },
                    "tooltip": [{"field": "마감 월"}, {"field": "공고 수"}],  # 마우스를 올리면 보이는 정보
                },
                # layer: 그림 두 장을 겹쳐 그린다
                "layer": [
                    {"mark": {"type": "line", "point": True}},  # 1) 선 + 각 월에 점
                    {  # 2) 점 위에 개수 숫자 (dy=-12: 점보다 12픽셀 위)
                        "mark": {**NUMBER_TEXT, "dy": -12},
                        "encoding": {"text": {"field": "공고 수"}},
                    },
                ],
            },
            width="stretch",  # 칸 폭에 맞춤
        )

    # ── 오른쪽: 활동 유형별 공고 수 (가로 막대 그래프) ──
    with right:
        st.subheader("활동 유형별 공고 수")
        # value_counts()는 개수가 많은 순서대로 정렬해 준다
        by_category = filtered["category"].value_counts()
        by_category = by_category.rename_axis("활동 유형").reset_index(name="공고 수")
        # 화면에 보일 때만 한글 이름으로 바꾼다 (korean_names는 사이드바에서 만든 것, filtered는 영어 그대로)
        by_category["활동 유형"] = by_category["활동 유형"].replace(korean_names)  # 목록에 없는 유형은 그대로 둔다
        # 막대 끝 숫자가 오른쪽에서 잘리지 않도록 x축 최댓값을 25% 넉넉하게 잡는다
        x_right = int(by_category["공고 수"].max() * 1.25) + 1
        # 가로 막대: x축에 숫자(공고 수), y축에 이름(활동 유형)을 놓는다
        st.vega_lite_chart(
            by_category,
            {
                "height": 300,
                # 막대와 숫자가 같이 쓰는 x·y 설정
                "encoding": {
                    "x": {
                        "field": "공고 수",
                        "type": "quantitative",
                        "title": None,
                        "scale": {"domain": [0, x_right]},
                        # tickCount=3: 아래 눈금 숫자를 3개 정도로 줄인다 (막대 끝 숫자로 값을 읽으므로)
                        "axis": {"tickCount": 3, "tickMinStep": 1, **AXIS_LABEL},
                    },
                    "y": {
                        "field": "활동 유형",
                        "type": "nominal",
                        # 큰 순서 목록을 직접 넘긴다 (by_category는 value_counts()로 이미 큰 순서)
                        # 막대+숫자를 겹쳐 그리면(layer) "-x" 정렬이 무시되고 가나다순이 되기 때문
                        "sort": by_category["활동 유형"].tolist(),
                        "title": None,
                        "axis": AXIS_LABEL,  # 왼쪽 이름 크게·굵게·진하게
                    },
                    "tooltip": [{"field": "활동 유형"}, {"field": "공고 수"}],
                },
                "layer": [
                    {  # 1) 막대
                        "mark": "bar",
                        "encoding": {
                            # 막대 색: 유형 이름(domain)과 색(range)을 짝지어 고정한다
                            # 전체 유형(all_categories) 기준으로 만들어서, 필터로 일부만 남아도 색이 바뀌지 않는다
                            "color": {
                                "field": "활동 유형",
                                "type": "nominal",
                                "scale": {
                                    "domain": [korean_names.get(c, c) for c in all_categories],
                                    "range": [color_codes.get(c, OTHER_COLOR_CODE) for c in all_categories],
                                },
                                "legend": None,  # 왼쪽에 이름이 이미 있으니 범례는 숨긴다
                            },
                        },
                    },
                    {  # 2) 막대 끝 오른쪽에 개수 숫자 (align=left, dx=6: 막대 끝에서 6픽셀 오른쪽)
                        "mark": {**NUMBER_TEXT, "align": "left", "dx": 6},
                        "encoding": {"text": {"field": "공고 수"}},
                    },
                ],
            },
            width="stretch",
        )

with tab_detail:
    # 조건에 맞는 데이터를 표로 보여 준다
    # width="stretch": 화면 폭에 맞춤 / hide_index=True: 왼쪽 행 번호 숨김
    st.dataframe(filtered, width="stretch", hide_index=True)

# ── 화면 맨 아래: 판단 문구 (탭 밖이라 어느 탭에서든 보인다) ──
# 0건이면 위에서 st.stop()으로 멈추므로 이 부분도 자동으로 안 보인다
# 주의: 아래 숫자는 전체 공고 기준으로 직접 적은 글이라, 조건을 바꾸거나 데이터가 바뀌어도 그대로다
st.subheader("이 화면으로 내릴 수 있는 판단 (전체 공고 기준)")
# st.info: 파란 안내 박스 / "- "로 시작하는 줄은 목록(글머리표)으로 보인다
st.info(
    "- 수집한 27개 공고 중 12월 마감 공고가 12건으로 가장 많아, 해당 기간에 공고 추천과 마감 알림을 "
    "집중적으로 제공하는 방안을 검토한다.\n"
    "- 또한 공모전(16건)에 비해 봉사활동(4건)의 수집 비중이 낮으므로, "
    "사용자에게 다양한 활동 기회를 제공하기 위해 봉사활동 공고 수집을 확대한다."
)
