# -*- coding: utf-8 -*-

import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import time
# مكتبات النصوص العربية
import arabic_reshaper
from bidi.algorithm import get_display

# Local modules
from utils.db_operations import (
    validate_session, get_complaint_details, 
    get_user_complaints, update_user_activity
)
from utils.text_processing import reshape_arabic
from utils.ai_processing import analyze_complaint_text
from data.constants import (
    WILAYAS, COMPLAINT_CATEGORIES, COMPLAINT_CATEGORIES_EN,
    COMPLAINT_STATUS, COMPLAINT_STATUS_EN, COMPLAINT_STATUS_COLORS,
    COMPLAINT_PRIORITIES, COMPLAINT_PRIORITIES_EN, COMPLAINT_PRIORITY_COLORS,
    LANGUAGES
)

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة الشكاوى الحكومية",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- وظائف مساعدة ---
def set_lang(lang_code):
    """تعيين لغة التطبيق"""
    st.session_state.lang = lang_code

def get_text(ar_text, fr_text=None, en_text=None):
    """الحصول على النص باللغة المحددة"""
    if "lang" not in st.session_state:
        st.session_state.lang = "ar"
        
    if st.session_state.lang == "fr" and fr_text:
        return fr_text
    elif st.session_state.lang == "en" and en_text:
        return en_text
    return reshape_arabic(ar_text)

def is_authenticated():
    """التحقق من حالة تسجيل الدخول"""
    if 'session_id' not in st.session_state:
        return False, None
    
    user = validate_session(st.session_state.session_id)
    if user:
        return True, user.id
    
    # إذا انتهت الجلسة، إزالة البيانات من الجلسة
    if 'session_id' in st.session_state:
        del st.session_state.session_id
    if 'user_id' in st.session_state:
        del st.session_state.user_id
    return False, None

def show_status_badge(status):
    """عرض شارة الحالة بألوان مناسبة"""
    status_color = COMPLAINT_STATUS_COLORS.get(status, "secondary")
    
    if st.session_state.lang == "en":
        status_text = COMPLAINT_STATUS_EN.get(status, status)
    else:
        status_text = COMPLAINT_STATUS.get(status, status)
    
    if status_color == "success":
        st.success(status_text)
    elif status_color == "warning":
        st.warning(status_text)
    elif status_color == "danger":
        st.error(status_text)
    else:
        st.info(status_text)

def show_progress_bar(status):
    """عرض شريط التقدم بناءً على حالة الشكوى"""
    progress = {
        "pending": 25,
        "processing": 75,
        "resolved": 100,
        "rejected": 100
    }
    
    progress_value = progress.get(status, 0) / 100.0
    st.progress(progress_value)

def format_datetime(iso_date):
    """تنسيق التاريخ والوقت"""
    if isinstance(iso_date, str):
        try:
            dt = datetime.fromisoformat(iso_date)
        except ValueError:
            # إذا كان التنسيق غير متوافق
            return iso_date
    else:
        dt = iso_date
    
    formatted_date = dt.strftime("%Y-%m-%d %H:%M")
    return formatted_date

def load_css():
    """تحميل ملف CSS المخصص"""
    # إضافة التصميم المخصص
    st.markdown("""
    <style>
        body {
            direction: rtl;
        }
        .stApp {
            font-family: 'Tajawal', 'Arial', sans-serif;
        }
        .en-text {
            direction: ltr;
            text-align: left;
        }
        .ar-text {
            direction: rtl;
            text-align: right;
        }
        .complaint-card {
            border: 1px solid #e6e6e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            transition: all 0.3s;
        }
        .complaint-card:hover {
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .header-with-line {
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .button-container {
            display: flex;
            justify-content: flex-end;
            margin-top: 20px;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        /* Status colors */
        .status-pending { background-color: #FFF3CD; color: #856404; }
        .status-processing { background-color: #D1ECF1; color: #0C5460; }
        .status-resolved { background-color: #D4EDDA; color: #155724; }
        .status-rejected { background-color: #F8D7DA; color: #721C24; }
    </style>
    """, unsafe_allow_html=True)

def show_login_page():
    """عرض صفحة تسجيل الدخول"""
    st.title(get_text("تسجيل الدخول", en_text="Login"))
    
    # تبديل بين تسجيل الدخول والتسجيل الجديد
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False
    
    tab_labels = [get_text("تسجيل الدخول", en_text="Login"), get_text("إنشاء حساب جديد", en_text="Create New Account")]
    current_tab = 0 if not st.session_state.show_signup else 1
    
    tab1, tab2 = st.tabs(tab_labels)
    
    with tab1:
        if not st.session_state.show_signup:
            # نموذج تسجيل الدخول
            with st.form("login_form"):
                username = st.text_input(get_text("اسم المستخدم", en_text="Username"))
                password = st.text_input(get_text("كلمة المرور", en_text="Password"), type="password")
                
                submit_button = st.form_submit_button(get_text("تسجيل الدخول", en_text="Login"))
                
                if submit_button:
                    if username and password:
                        from utils.db_operations import authenticate_user
                        
                        auth_result = authenticate_user(username, password)
                        if auth_result:
                            user_id, session_id = auth_result
                            
                            st.session_state.session_id = session_id
                            st.session_state.user_id = user_id
                            
                            st.success(get_text("تم تسجيل الدخول بنجاح!", en_text="Login successful!"))
                            st.rerun()
                        else:
                            st.error(get_text("اسم المستخدم أو كلمة المرور غير صحيحة", en_text="Invalid username or password"))
                    else:
                        st.warning(get_text("يرجى إدخال اسم المستخدم وكلمة المرور", en_text="Please enter username and password"))
    
    with tab2:
        if st.session_state.show_signup or current_tab == 1:
            # نموذج إنشاء حساب جديد
            with st.form("signup_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    username = st.text_input(get_text("اسم المستخدم", en_text="Username"), key="signup_username")
                    email = st.text_input(get_text("البريد الإلكتروني", en_text="Email"))
                    password = st.text_input(get_text("كلمة المرور", en_text="Password"), type="password", key="signup_password")
                
                with col2:
                    name = st.text_input(get_text("الاسم الكامل", en_text="Full Name"))
                    phone = st.text_input(get_text("رقم الهاتف", en_text="Phone Number"))
                    national_id = st.text_input(get_text("رقم الهوية الوطنية", en_text="National ID"))
                
                submit_button = st.form_submit_button(get_text("إنشاء حساب", en_text="Create Account"))
                
                if submit_button:
                    if username and email and password and name and phone and national_id:
                        from utils.db_operations import create_user
                        from utils.text_processing import validate_email_address, validate_phone
                        
                        # التحقق من صحة البريد الإلكتروني
                        is_valid_email, normalized_email = validate_email_address(email)
                        if not is_valid_email:
                            st.error(get_text("البريد الإلكتروني غير صحيح", en_text="Invalid email address"))
                            return
                        
                        # التحقق من صحة رقم الهاتف
                        if not validate_phone(phone):
                            st.error(get_text("رقم الهاتف غير صحيح", en_text="Invalid phone number"))
                            return
                        
                        # إنشاء المستخدم الجديد
                        user_id = create_user(username, password, email, phone, name, national_id)
                        
                        if user_id:
                            st.success(get_text("تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.", en_text="Account created successfully! You can now login."))
                            st.session_state.show_signup = False
                            st.rerun()
                        else:
                            st.error(get_text("حدث خطأ أثناء إنشاء الحساب. قد يكون اسم المستخدم أو البريد الإلكتروني مستخدم بالفعل.", en_text="An error occurred during account creation. Username or email may already be in use."))
                    else:
                        st.warning(get_text("يرجى إدخال جميع المعلومات المطلوبة", en_text="Please enter all required information"))
    
    # زر تبديل العرض
    toggle_text = get_text("ليس لديك حساب؟ أنشئ واحدًا الآن", en_text="Don't have an account? Create one now") if not st.session_state.show_signup else get_text("لديك حساب بالفعل؟ سجّل دخولك", en_text="Already have an account? Login now")
    
    if st.button(toggle_text):
        st.session_state.show_signup = not st.session_state.show_signup
        st.rerun()

def show_sidebar():
    """عرض الشريط الجانبي بالقائمة الرئيسية"""
    # عنوان الشريط الجانبي
    st.sidebar.title(get_text("نظام إدارة الشكاوى", en_text="Complaints Management"))
    
    # إظهار معلومات المستخدم الحالي
    authenticated, user_id = is_authenticated()
    
    if authenticated:
        from utils.db_operations import get_user_data
        
        # الحصول على بيانات المستخدم
        user = get_user_data(user_id)
        if user:
            st.sidebar.markdown(f"**{get_text('مرحبًا', en_text='Hello')}** {user.name}")
            st.sidebar.markdown(f"**{get_text('البريد الإلكتروني', en_text='Email')}:** {user.email}")
    
    # روابط التنقل
    st.sidebar.markdown("---")
    if st.sidebar.button(get_text("الصفحة الرئيسية", en_text="Home")):
        st.switch_page("app.py")
    
    if authenticated:
        if st.sidebar.button(get_text("تقديم شكوى جديدة", en_text="Submit New Complaint")):
            st.switch_page("pages/complaint_form.py")
        
        if st.sidebar.button(get_text("متابعة الشكاوى", en_text="Track Complaints")):
            st.switch_page("pages/complaints_tracker.py")
        
        if st.sidebar.button(get_text("الملف الشخصي", en_text="Profile")):
            st.switch_page("pages/profile.py")
        
        # تسجيل الخروج
        st.sidebar.markdown("---")
        if st.sidebar.button(get_text("تسجيل الخروج", en_text="Logout")):
            if 'session_id' in st.session_state:
                from utils.db_operations import end_session
                end_session(st.session_state.session_id)
                del st.session_state.session_id
            if 'user_id' in st.session_state:
                del st.session_state.user_id
            st.rerun()
    
    # روابط إضافية
    st.sidebar.markdown("---")
    if st.sidebar.button(get_text("الأسئلة الشائعة", en_text="FAQ")):
        st.switch_page("pages/faq.py")
    
    # قسم المسؤول
    if authenticated:
        from utils.db_operations import is_admin
        
        if is_admin(user_id):
            st.sidebar.markdown("---")
            st.sidebar.subheader(get_text("لوحة المسؤول", en_text="Admin Panel"))
            
            if st.sidebar.button(get_text("لوحة الإدارة", en_text="Admin Dashboard")):
                st.switch_page("pages/admin.py")
            
            if st.sidebar.button(get_text("التحليلات والإحصائيات", en_text="Analytics & Statistics")):
                st.switch_page("pages/analytics.py")
    
    # تغيير اللغة
    st.sidebar.markdown("---")
    lang_col1, lang_col2, lang_col3 = st.sidebar.columns(3)
    
    with lang_col1:
        if st.button("🇩🇿", help="العربية"):
            set_lang("ar")
            st.rerun()
    
    with lang_col2:
        if st.button("🇫🇷", help="Français"):
            set_lang("fr")
            st.rerun()
    
    with lang_col3:
        if st.button("🇬🇧", help="English"):
            set_lang("en")
            st.rerun()

def show_home_page():
    """عرض الصفحة الرئيسية"""
    # عنوان الصفحة
    st.title(get_text("نظام إدارة الشكاوى الحكومية", en_text="Government Complaints Management System"))
    
    # وصف النظام
    st.markdown(get_text(
        "<div style='direction: rtl; text-align: right;'>مرحبًا بكم في نظام إدارة الشكاوى الحكومية. يتيح هذا النظام للمواطنين تقديم شكاواهم المتعلقة بالخدمات البلدية ومتابعة حالتها والحصول على تحديثات بشأنها.</div>",
        en_text="<div>Welcome to the Government Complaints Management System. This system allows citizens to submit complaints related to municipal services, track their status, and receive updates about them.</div>"
    ), unsafe_allow_html=True)
    
    # التحقق من حالة تسجيل الدخول
    authenticated, user_id = is_authenticated()
    
    if authenticated:
        # تحديث نشاط المستخدم
        update_user_activity(user_id)
        
        # عرض الإحصائيات
        st.markdown("---")
        st.subheader(get_text("لوحة التحكم", en_text="Dashboard"))
        
        # الحصول على شكاوى المستخدم
        complaints = get_user_complaints(user_id)
        
        # عرض إحصائيات الشكاوى
        col1, col2, col3 = st.columns(3)
        
        total_complaints = len(complaints)
        pending_complaints = sum(1 for c in complaints if c.status in ["pending", "processing"])
        resolved_complaints = sum(1 for c in complaints if c.status == "resolved")
        
        with col1:
            st.metric(get_text("إجمالي الشكاوى", en_text="Total Complaints"), total_complaints)
        
        with col2:
            st.metric(get_text("الشكاوى قيد المعالجة", en_text="Pending Complaints"), pending_complaints)
        
        with col3:
            st.metric(get_text("الشكاوى المحلولة", en_text="Resolved Complaints"), resolved_complaints)
        
        # الروابط السريعة
        st.markdown("---")
        st.subheader(get_text("الروابط السريعة", en_text="Quick Links"))
        
        row1_col1, row1_col2 = st.columns(2)
        
        with row1_col1:
            if st.button(get_text("📝 تقديم شكوى جديدة", en_text="📝 Submit New Complaint"), use_container_width=True):
                st.switch_page("pages/complaint_form.py")
        
        with row1_col2:
            if st.button(get_text("📊 متابعة الشكاوى", en_text="📊 Track Complaints"), use_container_width=True):
                st.switch_page("pages/complaints_tracker.py")
        
        # آخر الشكاوى المقدمة
        st.markdown("---")
        st.subheader(get_text("آخر الشكاوى المقدمة", en_text="Latest Complaints"))
        
        if complaints:
            # عرض آخر 3 شكاوى
            recent_complaints = sorted(complaints, key=lambda x: x.created_at, reverse=True)[:3]
            
            for complaint in recent_complaints:
                show_complaint_card(complaint.id, complaint)
        else:
            st.info(get_text("لم تقم بتقديم أي شكاوى بعد. استخدم زر 'تقديم شكوى جديدة' لتقديم شكوى.", en_text="You haven't submitted any complaints yet. Use the 'Submit New Complaint' button to submit a complaint."))
    
    else:
        # عرض نموذج تسجيل الدخول
        show_login_page()
        
        # عرض الميزات الرئيسية للنظام
        st.markdown("---")
        st.subheader(get_text("مميزات النظام", en_text="System Features"))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"### {get_text('سهولة تقديم الشكاوى', en_text='Easy Complaint Submission')}")
            st.markdown(get_text(
                "<div style='direction: rtl; text-align: right;'>تقديم شكاوى بطريقة بسيطة ومنظمة مع إمكانية إرفاق المستندات الداعمة والصور.</div>",
                en_text="<div>Submit complaints in a simple and organized way with the ability to attach supporting documents and images.</div>"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"### {get_text('متابعة حالة الشكاوى', en_text='Complaint Status Tracking')}")
            st.markdown(get_text(
                "<div style='direction: rtl; text-align: right;'>متابعة حالة الشكاوى في الوقت الفعلي والحصول على تحديثات بشأنها من المسؤولين.</div>",
                en_text="<div>Track the status of complaints in real-time and receive updates about them from administrators.</div>"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"### {get_text('التواصل مع المسؤولين', en_text='Communication with Officials')}")
            st.markdown(get_text(
                "<div style='direction: rtl; text-align: right;'>التواصل المباشر مع المسؤولين عن معالجة الشكاوى وتبادل المعلومات اللازمة.</div>",
                en_text="<div>Direct communication with officials responsible for handling complaints and exchanging necessary information.</div>"
            ), unsafe_allow_html=True)
        
        # كيفية استخدام النظام
        st.markdown("---")
        st.subheader(get_text("كيفية استخدام النظام", en_text="How to Use the System"))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"1. {get_text('إنشاء حساب', en_text='Create an account')}")
        
        with col2:
            st.markdown(f"2. {get_text('تقديم شكوى', en_text='Submit a complaint')}")
        
        with col3:
            st.markdown(f"3. {get_text('متابعة الحالة', en_text='Track the status')}")

def show_new_complaint_page():
    """عرض صفحة تقديم شكوى جديدة"""
    pass  # تم نقلها إلى ملف منفصل

def show_track_complaints_page():
    """عرض صفحة متابعة الشكاوى"""
    pass  # تم نقلها إلى ملف منفصل

def show_complaint_card(complaint_id, complaint):
    """عرض بطاقة الشكوى"""
    with st.container():
        st.markdown(f"""
        <div class="complaint-card">
            <h4>{reshape_arabic(complaint.title)}</h4>
            <p><strong>{get_text("رقم التتبع", en_text="Tracking Number")}:</strong> {complaint.tracking_number}</p>
            <p><strong>{get_text("التاريخ", en_text="Date")}:</strong> {format_datetime(complaint.created_at)}</p>
            <p><strong>{get_text("الحالة", en_text="Status")}:</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        show_status_badge(complaint.status)
        show_progress_bar(complaint.status)
        
        if st.button(get_text("عرض التفاصيل", en_text="View Details"), key=f"view_{complaint_id}"):
            st.session_state.selected_complaint = complaint_id
            st.switch_page("pages/complaints_tracker.py")

def show_complaint_details_page():
    """عرض صفحة تفاصيل الشكوى"""
    pass  # تم نقلها إلى ملف منفصل

def show_profile_page():
    """عرض صفحة الملف الشخصي"""
    pass  # تم نقلها إلى ملف منفصل

def show_faq_page():
    """عرض صفحة الأسئلة الشائعة"""
    pass  # تم نقلها إلى ملف منفصل

def main():
    """الدالة الرئيسية للتطبيق"""
    # تحميل التصميم المخصص
    load_css()
    
    # عرض الشريط الجانبي
    show_sidebar()
    
    # عرض الصفحة الرئيسية
    show_home_page()

if __name__ == "__main__":
    main()