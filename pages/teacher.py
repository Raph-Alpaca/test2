import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# ---- 1. Supabase 설정 ----
@st.cache_resource
def get_supabase_client() -> Client:
    # 학생용 앱과 동일한 secrets를 사용한다고 가정합니다.
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)

def fetch_data():
    supabase = get_supabase_client()
    # 전체 제출 데이터 가져오기 (단순 쿼리)
    response = supabase.table("student_submissions").select("*").execute()
    return response.data

# ---- 2. 페이지 레이아웃 설정 ----
st.set_page_config(page_title="교사용 채점 대시보드", layout="wide")

st.title("👨‍🏫 서술형 평가 결과 대시보드")
st.markdown("학생들이 제출한 답안과 AI 피드백 결과를 실시간으로 확인합니다.")

# 데이터 불러오기
try:
    data = fetch_data()
    if not data:
        st.info("아직 제출된 데이터가 없습니다.")
        st.stop()
    
    df = pd.DataFrame(data)
    # 날짜 형식 변환
    df['created_at'] = pd.to_datetime(df['created_at'])

    # ---- 3. 요약 통계 (Metrics) ----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 제출 인원", f"{len(df)}명")
    
    # 문항별 정답(O) 비율 계산
    q1_pass = df['feedback_1'].str.startswith("O:").sum()
    q2_pass = df['feedback_2'].str.startswith("O:").sum()
    q3_pass = df['feedback_3'].str.startswith("O:").sum()
    
    with col2:
        st.metric("문항 1 정답률", f"{(q1_pass/len(df)*100):.1f}%")
    with col3:
        st.metric("문항 2 정답률", f"{(q2_pass/len(df)*100):.1f}%")
    with col4:
        st.metric("문항 3 정답률", f"{(q3_pass/len(df)*100):.1f}%")

    st.divider()

    # ---- 4. 시각화 섹션 ----
    st.subheader("📊 문항별 정답 현황")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # 문항별 O/X 통계 그래프
        pass_counts = pd.DataFrame({
            '문항': ['문항 1', '문항 2', '문항 3'],
            '정답수': [q1_pass, q2_pass, q3_pass],
            '오답수': [len(df)-q1_pass, len(df)-q2_pass, len(df)-q3_pass]
        })
        fig = px.bar(pass_counts, x='문항', y=['정답수', '오답수'], 
                     title="문항별 합격 여부", barmode='group',
                     color_discrete_map={'정답수': '#2ecc71', '오답수': '#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        # 시간대별 제출 현황
        df_time = df.set_index('created_at').resample('H').size().reset_index(name='count')
        fig_time = px.line(df_time, x='created_at', y='count', title="시간대별 제출 추이", markers=True)
        st.plotly_chart(fig_time, use_container_width=True)

    # ---- 5. 상세 데이터 필터링 및 조회 ----
    st.divider()
    st.subheader("🔍 학생별 상세 답안 확인")
    
    # 학번 검색 기능
    search_id = st.text_input("학번으로 검색", placeholder="예: 10130")
    if search_id:
        display_df = df[df['student_id'].str.contains(search_id)]
    else:
        display_df = df

    # 선택한 학생 상세 보기
    if not display_df.empty:
        selected_student = st.selectbox("상세 정보를 확인할 학생을 선택하세요", 
                                        options=display_df['student_id'].tolist())
        
        row = display_df[display_df['student_id'] == selected_student].iloc[0]
        
        detail_col1, detail_col2 = st.columns([1, 1])
        
        with detail_col1:
            st.info(f"**[문항 1 답안]**\n\n{row['answer_1']}")
            st.success(f"**[AI 피드백]**\n\n{row['feedback_1']}")
            
            st.info(f"**[문항 2 답안]**\n\n{row['answer_2']}")
            st.success(f"**[AI 피드백]**\n\n{row['feedback_2']}")

        with detail_col2:
            st.info(f"**[문항 3 답안]**\n\n{row['answer_3']}")
            st.success(f"**[AI 피드백]**\n\n{row['feedback_3']}")
            
            st.write(f"📅 제출 시간: {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"🤖 사용 모델: {row['model']}")
    
    # ---- 6. 전체 데이터 테이블 (다운로드 가능) ----
    st.divider()
    st.subheader("📋 전체 결과 데이터")
    st.dataframe(df.sort_values(by="created_at", ascending=False))
    
    # CSV 다운로드 버튼
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="CSV 파일로 내보내기",
        data=csv,
        file_name=f"evaluation_results_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime='text/csv',
    )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("Supabase 설정 및 테이블 컬럼명이 학생용 코드와 일치하는지 확인하세요.")
