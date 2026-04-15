import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="نظام متابعة إكسباير صيدليات ليمون", layout="wide")

st.title("📊 نظام تحليل ومتابعة صلاحية الأدوية")
st.sidebar.header("إعدادات البيانات")

# 1. رفع الملفات
old_file = st.sidebar.file_uploader("ارفع الشيت القديم (CSV/Excel)", type=['csv', 'xlsx'])
new_file = st.sidebar.file_uploader("ارفع الشيت الأحدث (CSV/Excel)", type=['csv', 'xlsx'])

# إدخال تواريخ الشيتات لحساب الفرق الزمني بدقة
date_old = st.sidebar.date_input("تاريخ الشيت القديم", value=datetime(2026, 3, 1))
date_new = st.sidebar.date_input("تاريخ الشيت الأحدث", value=datetime(2026, 4, 1))

days_diff = (date_new - date_old).days

if old_file and new_file and days_diff > 0:
    df_old = pd.read_csv(old_file) if old_file.name.endswith('csv') else pd.read_excel(old_file)
    df_new = pd.read_csv(new_file) if new_file.name.endswith('csv') else pd.read_excel(new_file)

    # تنظيف البيانات
    df_new['تاريخ الصلاحية'] = pd.to_datetime(df_new['تاريخ الصلاحية'])
    
    # دمج الملفين بناءً على الباركود واسم الصنف
    merged = pd.merge(df_new, df_old[['الباركود', 'الرصيد']], on='الباركود', suffixes=('_جديد', '_قديم'))
    
    # حساب معدل التناقص اليومي
    merged['معدل_السحب_اليومي'] = (merged['الرصيد_قديم'] - merged['الرصيد_جديد']) / days_diff
    merged['معدل_السحب_اليومي'] = merged['معدل_السحب_اليومي'].clip(lower=0) # نمنع السحب السالب في حال زيادة الرصيد
    
    # حساب الأيام المتبقية للإكسباير
    merged['أيام_حتى_الإكسباير'] = (merged['تاريخ الصلاحية'] - pd.Timestamp.now()).dt.days
    
    # التنبؤ بالكمية الراكدة
    # الكمية الحالية - (المعدل * الأيام المتبقية)
    merged['الكمية_الراكدة_المتوقعة'] = merged['الرصيد_جديد'] - (merged['معدل_السحب_اليومي'] * merged['أيام_حتى_الإكسباير'])
    merged['الكمية_الراكدة_المتوقعة'] = merged['الكمية_الراكدة_المتوقعة'].apply(lambda x: x if x > 0 else 0)
    merged['قيمة_الخسارة_المتوقعة'] = merged['الكمية_الراكدة_المتوقعة'] * merged['سعر الجمهور']

    # --- الجزء الخاص بالداشبورد ---
    st.subheader("📈 نظرة عامة على حالة الإكسباير")
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي القيمة المعرضة للإكسباير", f"{merged['الاجمالي'].sum():,.2f} ريال")
    col2.metric("خسارة متوقعة (بسبب ضعف السحب)", f"{merged['قيمة_الخسارة_المتوقعة'].sum():,.2f} ريال")
    col3.metric("عدد الأصناف الخطرة", len(merged[merged['الكمية_الراكدة_المتوقعة'] > 0]))

    # تجميع حسب الشهر والسنة
    merged['شهر_السنة'] = merged['تاريخ الصلاحية'].dt.to_period('M').astype(str)
    monthly_summary = merged.groupby('شهر_السنة').agg({
        'الاجمالي': 'sum',
        'قيمة_الخسارة_المتوقعة': 'sum',
        'الباركود': 'count'
    }).reset_index()

    st.bar_chart(monthly_summary.set_index('شهر_السنة')['الاجمالي'])

    # تفاصيل الشهر
    selected_month = st.selectbox("اختر شهر لاستعراض التفاصيل", monthly_summary['شهر_السنة'].unique())
    if selected_month:
        month_details = merged[merged['شهر_السنة'] == selected_month]
        st.write(f"أصناف شهر {selected_month}:")
        st.dataframe(month_details[['اسم الصنف', 'الرصيد_جديد', 'معدل_السحب_اليومي', 'الكمية_الراكدة_المتوقعة', 'قيمة_الخسارة_المتوقعة']])

else:
    st.info("من فضلك ارفع الشيت القديم والجديد لتبدأ عملية التحليل.")
