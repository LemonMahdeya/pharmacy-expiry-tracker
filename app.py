import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="نظام متابعة إكسباير صيدليات ليمون", layout="wide")

st.title("📊 نظام تحليل ومتابعة صلاحية الأدوية")
st.sidebar.header("إعدادات البيانات")

# 1. رفع الملفات
old_file = st.sidebar.file_uploader("ارفع الشيت القديم (CSV/Excel)", type=['csv', 'xlsx'])
new_file = st.sidebar.file_uploader("ارفع الشيت الأحدث (CSV/Excel)", type=['csv', 'xlsx'])

date_old = st.sidebar.date_input("تاريخ الشيت القديم", value=datetime(2026, 3, 1))
date_new = st.sidebar.date_input("تاريخ الشيت الأحدث", value=datetime(2026, 4, 1))

days_diff = (date_new - date_old).days

if old_file and new_file and days_diff > 0:
    def load_and_clean(file):
        df = pd.read_csv(file, encoding='utf-8-sig') if file.name.endswith('csv') else pd.read_excel(file)
        df.columns = df.columns.str.strip()
        
        # تحويل الأعمدة الرقمية ومعالجة النصوص المتكررة (مثل كلمة "الكمية" داخل الجدول)
        df['الكمية'] = pd.to_numeric(df['الكمية'], errors='coerce')
        df['سعر البيع'] = pd.to_numeric(df['سعر البيع'], errors='coerce')
        df['اجمالى البيع'] = pd.to_numeric(df['اجمالى البيع'], errors='coerce')
        
        # حذف الصفوف التي أصبحت فارغة بعد التحويل (التي كانت تحتوي على عناوين مكررة)
        df = df.dropna(subset=['الكمية', 'رقم الصنف'])
        return df

    df_old = load_and_clean(old_file)
    df_new = load_and_clean(new_file)

    # تحويل التاريخ
    df_new['تاريخ الانتهاء'] = pd.to_datetime(df_new['تاريخ الانتهاء'], errors='coerce')
    df_new = df_new.dropna(subset=['تاريخ الانتهاء'])
    
    # دمج الملفين
    merged = pd.merge(df_new, df_old[['رقم الصنف', 'الكمية']], on='رقم الصنف', suffixes=('_جديد', '_قديم'))
    
    # العمليات الحسابية
    merged['معدل_السحب_اليومي'] = (merged['الكمية_قديم'] - merged['الكمية_جديد']) / days_diff
    merged['معدل_السحب_اليومي'] = merged['معدل_السحب_اليومي'].clip(lower=0)
    
    merged['أيام_حتى_الإكسباير'] = (merged['تاريخ الانتهاء'] - pd.Timestamp.now()).dt.days
    
    # التنبؤ بالراكد
    merged['الكمية_الراكدة_المتوقعة'] = merged['الكمية_جديد'] - (merged['معدل_السحب_اليومي'] * merged['أيام_حتى_الإكسباير'])
    merged['الكمية_الراكدة_المتوقعة'] = merged['الكمية_الراكدة_المتوقعة'].clip(lower=0)
    merged['قيمة_الخسارة_المتوقعة'] = merged['الكمية_الراكدة_المتوقعة'] * merged['سعر البيع']

    # العرض
    st.subheader("📈 ملخص حالة المخزون")
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي قيمة الإكسباير", f"{merged['اجمالى البيع'].sum():,.2f}")
    c2.metric("خسارة متوقعة (راكد)", f"{merged['قيمة_الخسارة_المتوقعة'].sum():,.2f}")
    c3.metric("أصناف مهددة بالبقاء", len(merged[merged['الكمية_الراكدة_المتوقعة'] > 0]))

    # تجميع شهري للرسم البياني
    merged['شهر_السنة'] = merged['تاريخ الانتهاء'].dt.to_period('M').astype(str)
    monthly = merged.groupby('شهر_السنة')['اجمالى البيع'].sum().reset_index()
    
    st.bar_chart(monthly.set_index('شهر_السنة'))

    selected_month = st.selectbox("اختر شهر لاستعراض تفاصيله", sorted(merged['شهر_السنة'].unique()))
    if selected_month:
        det = merged[merged['شهر_السنة'] == selected_month].sort_values(by='الكمية_الراكدة_المتوقعة', ascending=False)
        st.dataframe(det[['اسم الصنف', 'الكمية_جديد', 'معدل_السحب_اليومي', 'الكمية_الراكدة_المتوقعة', 'قيمة_الخسارة_المتوقعة', 'تاريخ الانتهاء']])
else:
    st.info("من فضلك ارفع الشيت القديم والجديد لتبدأ عملية التحليل.")
