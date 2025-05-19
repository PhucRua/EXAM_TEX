import streamlit as st
import os
import re
import json
import uuid
import base64
import time
from datetime import datetime
from pathlib import Path

# Thiết lập giao diện Streamlit
st.set_page_config(
    page_title="Hệ thống thi trực tuyến",
    page_icon="📝",
    layout="wide"
)

# CSS cho giao diện
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
        color: #1E3A8A;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        color: #1E3A8A;
    }
    .question {
        padding: 1rem;
        background-color: #f0f5ff;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .solution {
        padding: 1rem;
        background-color: #f0fff4;
        border-left: 4px solid green;
        border-radius: 0.25rem;
        margin-top: 0.5rem;
    }
    .timer {
        font-size: 1.25rem;
        font-weight: bold;
        text-align: center;
        padding: 0.5rem;
        background-color: #e5edff;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
    }
    .result-box {
        padding: 1rem;
        background-color: #ebf8ff;
        border-radius: 0.5rem;
        margin-top: 1rem;
        text-align: center;
    }
    .exam-card {
        padding: 1rem;
        background-color: white;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Đường dẫn lưu trữ dữ liệu
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
EXAMS_FILE = DATA_DIR / "exams.json"
RESULTS_FILE = DATA_DIR / "results.json"

# Khởi tạo dữ liệu nếu chưa tồn tại
if not USERS_FILE.exists():
    with open(USERS_FILE, "w") as f:
        json.dump({
            "teacher": {"password": "teacher123", "name": "Giáo viên"},
            "student": {"password": "student123", "name": "Học sinh", "class": "12A1"}
        }, f)

if not EXAMS_FILE.exists():
    with open(EXAMS_FILE, "w") as f:
        json.dump([], f)

if not RESULTS_FILE.exists():
    with open(RESULTS_FILE, "w") as f:
        json.dump([], f)

# Hàm đọc dữ liệu
def read_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def read_exams():
    with open(EXAMS_FILE, "r") as f:
        return json.load(f)

def read_results():
    with open(RESULTS_FILE, "r") as f:
        return json.load(f)

# Hàm ghi dữ liệu
def write_exams(exams):
    with open(EXAMS_FILE, "w") as f:
        json.dump(exams, f, indent=2)

def write_results(results):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

# Hàm xử lý file TeX
def extract_questions_from_tex(tex_content):
    """Trích xuất các câu hỏi từ file TEX"""
    # Pattern cho câu trắc nghiệm
    pattern = r'\\begin{ex}(.*?)\\end{ex}'
    question_blocks = re.findall(pattern, tex_content, re.DOTALL)
    
    questions = []
    for q_block in question_blocks:
        # Trích xuất nội dung câu hỏi
        stem_match = re.search(r'(.*?)\\choice', q_block, re.DOTALL)
        stem = stem_match.group(1).strip() if stem_match else ""
        
        # Trích xuất các phương án và đáp án đúng
        options = []
        correct_answer = None
        
        options_pattern = r'{(\\True\s*)?(.*?)}'
        options_matches = re.findall(options_pattern, q_block)
        
        for i, (is_true, option_text) in enumerate(options_matches):
            options.append(option_text.strip())
            if is_true:
                correct_answer = i
        
        # Trích xuất lời giải
        solution_match = re.search(r'\\loigiai{(.*?)}', q_block, re.DOTALL)
        solution = solution_match.group(1).strip() if solution_match else ""
        
        # Thêm câu hỏi vào danh sách
        questions.append({
            "stem": stem,
            "options": options,
            "correct_answer": correct_answer,
            "solution": solution
        })
    
    return questions

# Phần đăng nhập
def login_page():
    st.markdown("<h1 class='main-header'>Đăng nhập hệ thống</h1>", unsafe_allow_html=True)
    
    users = read_users()
    
    username = st.text_input("Tên đăng nhập")
    password = st.text_input("Mật khẩu", type="password")
    
    if st.button("Đăng nhập"):
        if username in users and users[username]["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["user_type"] = "teacher" if username == "teacher" else "student"
            st.session_state["user_info"] = users[username]
            st.success(f"Đăng nhập thành công! Xin chào {users[username]['name']}")
            st.rerun()
        else:
            st.error("Tên đăng nhập hoặc mật khẩu không đúng")

# Giao diện giáo viên
def teacher_interface():
    st.markdown("<h1 class='main-header'>Trang quản lý đề thi</h1>", unsafe_allow_html=True)
    
    if st.sidebar.button("Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Tab để chọn giữa tạo đề thi mới và xem các đề thi đã tạo
    tab1, tab2 = st.tabs(["Tạo đề thi mới", "Quản lý đề thi"])
    
    with tab1:
        create_exam()
    
    with tab2:
        manage_exams()

def create_exam():
    st.markdown("<h2 class='sub-header'>Tạo đề thi mới</h2>", unsafe_allow_html=True)
    
    with st.form("create_exam_form"):
        exam_name = st.text_input("Tên đề thi")
        description = st.text_area("Mô tả đề thi")
        time_limit = st.number_input("Thời gian làm bài (phút)", min_value=5, value=60)
        
        # Danh sách lớp được phép làm bài
        classes = st.multiselect("Lớp được phép làm bài", ["10A1", "10A2", "11A1", "11A2", "12A1", "12A2"])
        
        # Tải lên file TeX
        uploaded_file = st.file_uploader("Tải lên file .tex", type="tex")
        
        submit_button = st.form_submit_button("Tạo đề thi")
        
        if submit_button:
            if not exam_name:
                st.error("Vui lòng nhập tên đề thi")
                return
                
            if not uploaded_file:
                st.error("Vui lòng tải lên file .tex")
                return
            
            # Đọc nội dung file
            tex_content = uploaded_file.read().decode("utf-8")
            
            # Trích xuất câu hỏi
            with st.spinner("Đang xử lý file .tex..."):
                questions = extract_questions_from_tex(tex_content)
                
                if not questions:
                    st.error("Không tìm thấy câu hỏi nào trong file .tex")
                    return
                
                # Tạo đề thi mới
                exam_id = str(uuid.uuid4())
                new_exam = {
                    "id": exam_id,
                    "name": exam_name,
                    "description": description,
                    "time_limit": time_limit,
                    "classes": classes,
                    "questions": questions,
                    "created_at": datetime.now().isoformat(),
                    "active": True
                }
                
                # Lưu đề thi
                exams = read_exams()
                exams.append(new_exam)
                write_exams(exams)
                
                st.success(f"Đã tạo đề thi thành công! (ID: {exam_id})")

def manage_exams():
    st.markdown("<h2 class='sub-header'>Quản lý đề thi</h2>", unsafe_allow_html=True)
    
    exams = read_exams()
    
    if not exams:
        st.info("Chưa có đề thi nào được tạo.")
        return
    
    # Hiển thị danh sách đề thi
    for i, exam in enumerate(exams):
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class='exam-card'>
                    <h3>{exam['name']}</h3>
                    <p>{exam['description']}</p>
                    <p>Thời gian: {exam['time_limit']} phút | Số câu hỏi: {len(exam['questions'])}</p>
                    <p>Lớp: {', '.join(exam['classes']) if exam['classes'] else 'Tất cả'}</p>
                    <p>Trạng thái: {'Kích hoạt' if exam['active'] else 'Vô hiệu'}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Nút để xem trước và quản lý
                if st.button("Xem trước", key=f"preview_{i}"):
                    st.session_state["preview_exam"] = exam
                    st.session_state["current_page"] = "preview_exam"
                    st.rerun()
                
                # Nút để xem kết quả
                if st.button("Kết quả", key=f"results_{i}"):
                    # Lọc kết quả cho đề thi này
                    results = read_results()
                    exam_results = [r for r in results if r["exam_id"] == exam["id"]]
                    
                    if not exam_results:
                        st.info(f"Chưa có học sinh nào làm đề thi '{exam['name']}'")
                    else:
                        # Hiển thị kết quả
                        st.markdown(f"<h3>Kết quả đề thi '{exam['name']}'</h3>", unsafe_allow_html=True)
                        
                        result_data = []
                        for r in exam_results:
                            score_percent = (r['score'] / r['total_questions']) * 100
                            result_data.append({
                                "Học sinh": r["student_name"],
                                "Điểm số": f"{r['score']}/{r['total_questions']}",
                                "Phần trăm": f"{score_percent:.1f}%",
                                "Thời gian làm": f"{int(r['duration'] // 60)}:{int(r['duration'] % 60):02d}",
                                "Ngày làm": datetime.fromisoformat(r["timestamp"]).strftime("%d/%m/%Y %H:%M")
                            })
                        
                        st.table(result_data)
                        
                        # Xuất CSV
                        csv = "Học sinh,Điểm số,Phần trăm,Thời gian làm,Ngày làm\n"
                        for r in result_data:
                            csv += f"{r['Học sinh']},{r['Điểm số']},{r['Phần trăm']},{r['Thời gian làm']},{r['Ngày làm']}\n"
                        
                        b64 = base64.b64encode(csv.encode()).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="ketqua_{exam["id"]}.csv">Tải xuống CSV</a>'
                        st.markdown(href, unsafe_allow_html=True)
                
                # Nút để kích hoạt/vô hiệu đề thi
                active_label = "Vô hiệu" if exam["active"] else "Kích hoạt"
                if st.button(active_label, key=f"toggle_{i}"):
                    exams[i]["active"] = not exams[i]["active"]
                    write_exams(exams)
                    st.rerun()

# Giao diện học sinh
def student_interface():
    st.markdown("<h1 class='main-header'>Danh sách đề thi</h1>", unsafe_allow_html=True)
    
    if st.sidebar.button("Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    user_info = st.session_state["user_info"]
    student_class = user_info.get("class", "")
    
    # Lấy danh sách đề thi có sẵn cho học sinh
    exams = read_exams()
    available_exams = []
    
    for exam in exams:
        if exam["active"] and (not exam["classes"] or student_class in exam["classes"]):
            available_exams.append(exam)
    
    if not available_exams:
        st.info("Hiện không có đề thi nào dành cho bạn.")
        return
    
    # Hiển thị danh sách đề thi
    st.markdown("<h2 class='sub-header'>Các đề thi có thể làm</h2>", unsafe_allow_html=True)
    
    for i, exam in enumerate(available_exams):
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class='exam-card'>
                    <h3>{exam['name']}</h3>
                    <p>{exam['description']}</p>
                    <p>Thời gian: {exam['time_limit']} phút | Số câu hỏi: {len(exam['questions'])}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("Làm bài", key=f"take_{i}"):
                    st.session_state["current_exam"] = exam
                    st.session_state["current_page"] = "take_exam"
                    st.session_state["start_time"] = time.time()
                    st.session_state["answers"] = [None] * len(exam["questions"])
                    st.rerun()

def preview_exam():
    """Xem trước đề thi - chế độ giáo viên"""
    exam = st.session_state["preview_exam"]
    
    st.markdown(f"<h1 class='main-header'>{exam['name']} (Xem trước)</h1>", unsafe_allow_html=True)
    st.markdown(f"<p>{exam['description']}</p>", unsafe_allow_html=True)
    st.markdown(f"<p>Thời gian: {exam['time_limit']} phút | Số câu hỏi: {len(exam['questions'])}</p>", unsafe_allow_html=True)
    
    if st.button("Quay lại"):
        st.session_state["current_page"] = "home"
        if "preview_exam" in st.session_state:
            del st.session_state["preview_exam"]
        st.rerun()
    
    # Hiển thị các câu hỏi
    tabs = st.tabs([f"Câu {i+1}" for i in range(len(exam["questions"]))])
    
    for i, tab in enumerate(tabs):
        with tab:
            question = exam["questions"][i]
            
            # Hiển thị nội dung câu hỏi
            st.markdown(f"<div class='question'>{question['stem']}</div>", unsafe_allow_html=True)
            
            # Hiển thị các phương án
            for j, option in enumerate(question["options"]):
                if j == question["correct_answer"]:
                    st.markdown(f"<p style='color: green; font-weight: bold;'>{chr(65+j)}. {option} ✓</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p>{chr(65+j)}. {option}</p>", unsafe_allow_html=True)
            
            # Hiển thị lời giải
            st.markdown(f"<div class='solution'><strong>Lời giải:</strong><br>{question['solution']}</div>", unsafe_allow_html=True)

def take_exam():
    """Làm bài thi - chế độ học sinh"""
    exam = st.session_state["current_exam"]
    
    # Kiểm tra nếu đã nộp bài
    if "submitted" not in st.session_state:
        st.session_state["submitted"] = False
    
    # Tính thời gian còn lại
    elapsed_time = time.time() - st.session_state["start_time"]
    remaining_time = max(0, exam["time_limit"] * 60 - elapsed_time)
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    
    # Nộp bài tự động khi hết thời gian
    if remaining_time <= 0 and not st.session_state["submitted"]:
        st.session_state["submitted"] = True
        submit_exam(exam)
    
    st.markdown(f"<h1 class='main-header'>{exam['name']}</h1>", unsafe_allow_html=True)
    
    # Hiển thị thời gian còn lại
    st.markdown(f"<div class='timer'>Thời gian còn lại: {minutes:02d}:{seconds:02d}</div>", unsafe_allow_html=True)
    
    if not st.session_state["submitted"]:
        # Nút nộp bài
        if st.button("Nộp bài"):
            st.session_state["submitted"] = True
            submit_exam(exam)
            st.rerun()
        
        # Hiển thị các câu hỏi
        tabs = st.tabs([f"Câu {i+1}" for i in range(len(exam["questions"]))])
        
        for i, tab in enumerate(tabs):
            with tab:
                question = exam["questions"][i]
                
                # Hiển thị nội dung câu hỏi bằng LaTeX
                st.latex(question["stem"])
                
                # Hiển thị các phương án
                options = [f"{chr(65+j)}. {option}" for j, option in enumerate(question["options"])]
                
                selected = st.radio(
                    "Chọn đáp án:",
                    options,
                    index=-1 if st.session_state["answers"][i] is None else st.session_state["answers"][i],
                    key=f"q_{i}"
                )
                
                if selected:
                    st.session_state["answers"][i] = options.index(selected)
    else:
        # Đã nộp bài, hiển thị kết quả
        show_exam_results(exam)
        
        # Nút quay lại
        if st.button("Quay lại danh sách đề thi"):
            # Xóa dữ liệu bài thi hiện tại
            del st.session_state["current_exam"]
            del st.session_state["current_page"]
            del st.session_state["start_time"]
            del st.session_state["answers"]
            del st.session_state["submitted"]
            if "score" in st.session_state:
                del st.session_state["score"]
            st.rerun()

def submit_exam(exam):
    """Xử lý nộp bài thi"""
    # Tính điểm
    score = 0
    for i, question in enumerate(exam["questions"]):
        if st.session_state["answers"][i] == question["correct_answer"]:
            score += 1
    
    # Lưu điểm
    st.session_state["score"] = score
    
    # Lưu kết quả vào cơ sở dữ liệu
    results = read_results()
    
    # Tính thời gian làm bài
    duration = time.time() - st.session_state["start_time"]
    
    result = {
        "id": str(uuid.uuid4()),
        "exam_id": exam["id"],
        "exam_name": exam["name"],
        "student_id": st.session_state["username"],
        "student_name": st.session_state["user_info"]["name"],
        "student_class": st.session_state["user_info"].get("class", ""),
        "score": score,
        "total_questions": len(exam["questions"]),
        "answers": st.session_state["answers"],
        "duration": duration,
        "timestamp": datetime.now().isoformat()
    }
    
    results.append(result)
    write_results(results)

def show_exam_results(exam):
    """Hiển thị kết quả bài thi"""
    score = st.session_state["score"]
    total = len(exam["questions"])
    percentage = (score / total) * 100 if total > 0 else 0
    
    st.markdown(f"""
    <div class='result-box'>
        <h2>Kết quả bài thi</h2>
        <p style='font-size: 1.5rem;'>Điểm số: {score}/{total} ({percentage:.1f}%)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Hiển thị đáp án và lời giải
    st.markdown("<h3>Đáp án và lời giải</h3>", unsafe_allow_html=True)
    
    # Hiển thị các câu hỏi
    tabs = st.tabs([f"Câu {i+1}" for i in range(len(exam["questions"]))])
    
    for i, tab in enumerate(tabs):
        with tab:
            question = exam["questions"][i]
            user_answer = st.session_state["answers"][i]
            correct_answer = question["correct_answer"]
            
            # Hiển thị nội dung câu hỏi
            st.latex(question["stem"])
            
            # Hiển thị các phương án
            for j, option in enumerate(question["options"]):
                if j == correct_answer:
                    st.markdown(f"<p style='color: green; font-weight: bold;'>{chr(65+j)}. {option} ✓</p>", unsafe_allow_html=True)
                elif j == user_answer:
                    if user_answer != correct_answer:
                        st.markdown(f"<p style='color: red;'>{chr(65+j)}. {option} ✗</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color: green; font-weight: bold;'>{chr(65+j)}. {option} ✓</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p>{chr(65+j)}. {option}</p>", unsafe_allow_html=True)
            
            # Hiển thị lời giải
            st.latex(question["solution"])

# Luồng chương trình chính
def main():
    # Khởi tạo session state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "home"
    
    # Kiểm tra đăng nhập
    if not st.session_state["logged_in"]:
        login_page()
        return
    
    # Xác định trang hiện tại
    current_page = st.session_state["current_page"]
    
    if current_page == "home":
        # Hiển thị giao diện phù hợp với vai trò
        if st.session_state["user_type"] == "teacher":
            teacher_interface()
        else:
            student_interface()
    
    elif current_page == "preview_exam":
        # Xem trước đề thi (giáo viên)
        preview_exam()
    
    elif current_page == "take_exam":
        # Làm bài thi (học sinh)
        take_exam()

if __name__ == "__main__":
    main()
