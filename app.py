import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="نظام متابعة إكسباير صيدليات ليمون", layout="wide")

st.title("📊 نظام تحليل ومتابعة صلاحية الأدوية")
st.sidebar.header("إعدادات البيانات")

# 1. رفع الملفات
old_file = st.sidebar.file_uploader("ارفع الشيت القديم (CSV/Excel)", type=['csv', 'xlsx'])
new_file = st.sidebar.file_uploader("ارفع الشيت الأحدث (CSV/Excel)", type=['csv', 'xlsx'])

# تواريخ الشيتات لحساب معدل السحب بدقة
date_old = st.sidebar.date_input("تاريخ الشيت القديم", value=datetime(2026, 3, 1))
date_new = st.sidebar.date_input("تاريخ الشيت الأحدث", value=datetime(2026, 4, 1))

days_diff = (date_new - date_old).days

if old_file and new_file and days_diff > 0:
    # وظيفة لقراءة الملفات وتنظيف الأعمدة
    def load_data(file):
        df = pd.read_csv(file, encoding='utf-8-sig') if file.name.endswith('csv') else pd.read_excel(file)
        df.columns = df.columns.str.strip() # تنظيف المسافات
        return df

    df_old = load_data(old_file)
    df_new = load_data(new_file)

    # تحويل التاريخ (باستخدام الاسم الصحيح: تاريخ الانتهاء)
    df_new['تاريخ الانتهاء'] = pd.to_datetime(df_new['تاريخ الانتهاء'], errors='coerce')
    
    # دمج الملفين بناءً على (رقم الصنف) بدلاً من الباركود
    merged = pd.merge(df_new, df_old[['رقم الصنف', 'الكمية']], on='رقم الصنف', suffixes=('_جديد', '_قديم'))
    
    # حساب معدل التناقص اليومي
    merged['معدل_السحب_اليومي'] = (merged['الكمية_قديم'] - merged['الكمية_جديد']) / days_diff
    merged['معدل_السحب_اليومي'] = merged['معدل_السحب_اليومي'].clip(lower=0)
    
    # حساب الأيام المتبقية للإكسباير
    merged['أيام_حتى_الإكسباير'] = (merged['تاريخ الانتهاء'] - pd.Timestamp.now()).dt.days
    
    # التنبؤ بالكمية الراكدة
    merged['الكمية_الراكدة_المتوقعة'] = merged['الكمية_جديد'] - (merged['معدل_السحب_اليومي'] * merged['أيام_حتى_الإكسباير'])
    merged['الكمية_الراكدة_المتوقعة'] = merged['الكمية_الراكدة_المتوقعة'].clip(lower=0)
    merged['قيمة_الخسارة_المتوقعة'] = merged['الكمية_الراكدة_المتوقعة'] * merged['سعر البيع']

    # --- الداشبورد ---
    st.subheader("📈 ملخص حالة المخزون")
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي قيمة الإكسباير", f"{merged['اجمالى البيع'].sum():,.2f}")
    c2.metric("خسارة متوقعة (راكد)", f"{merged['قيمة_الخسارة_المتوقعة'].sum():,.2f}")
    c3.metric("أصناف تحتاج تدخل", len(merged[merged['الكمية_الراكدة_المتوقعة'] > 0]))

    # تجميع شهري
    merged['شهر_السنة'] = merged['تاريخ الانتهاء'].dt.to_period('M').astype(str)
    monthly = merged.groupby('شهر_السنة')['اجمالى البيع'].sum().reset_index()
    
    st.bar_chart(monthly.set_index('شهر_السنة'))

    # تفاصيل الشهر
    selected_month = st.selectbox("اختر شهر لاستعراض تفاصيله", sorted(merged['شهر_السنة'].unique()))
    if selected_month:
        det = merged[merged['شهر_السنة'] == selected_month]
        st.dataframe(det[['اسم الصنف', 'الكمية_جديد', 'معدل_السحب_اليومي', 'الكمية_الراكدة_المتوقعة', 'تاريخ الانتهاء']])

else:
    st.warning("تأكد من رفع الملفين وأن تاريخ الشيت الجديد أحدث من القديم.")
