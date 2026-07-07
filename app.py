import streamlit as st
import pandas as pd
import altair as alt
import datetime

# 1. Настройки внешнего вида страницы
st.set_page_config(page_title="WB Analytics", layout="wide")

MONTHS_RU = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

if 'global_sku' not in st.session_state:
    st.session_state.global_sku = ""

tabs_list = ["🛒 Каталог товаров", "📈 Динамика товара (История)", "⚔️ Сравнение конкурентов (Рынок)"]
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = tabs_list[0]

def format_number(num):
    if pd.isna(num): return ""
    return f"{int(num):,}".replace(',', ' ')

@st.cache_data(ttl=60)
def load_sizes_data():
    url_sizes = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vS3RzvHV-huXWUxXTa9FZ2gJxUys_RH68FQJZA6ja4qi4cGq05dvz0FkLPTtsY8nUgs_HQHEUkFMgT1/pub?gid=967159777&single=true&output=csv'
    try:
        df_sizes = pd.read_csv(url_sizes)
        df_sizes.columns = df_sizes.columns.str.strip()
        if 'SKU' in df_sizes.columns:
            df_sizes['SKU'] = df_sizes['SKU'].astype(str).str.replace('.0', '', regex=False)
            
        numeric_cols = ['Корзины', 'Заказы', 'Выкупы', 'Отмены']
        for col in numeric_cols:
            if col in df_sizes.columns:
                df_sizes[col] = pd.to_numeric(df_sizes[col].astype(str).str.replace(r'\s+', '', regex=True), errors='coerce').fillna(0)
        return df_sizes
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_data():
    url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vS3RzvHV-huXWUxXTa9FZ2gJxUys_RH68FQJZA6ja4qi4cGq05dvz0FkLPTtsY8nUgs_HQHEUkFMgT1/pub?gid=1470204745&single=true&output=csv'
    df = pd.read_csv(url) 
    df.columns = df.columns.str.strip()
    
    # Обработка сдвигов столбцов
    if 'Фото' in df.columns: df = df.rename(columns={'Фото': 'Фото_ссылка'})
    elif 'Unnamed: 10' in df.columns and 'Цена' not in df.columns: df = df.rename(columns={'Unnamed: 10': 'Цена'})
    elif 'Unnamed: 11' in df.columns and 'Фото_ссылка' not in df.columns: df = df.rename(columns={'Unnamed: 11': 'Фото_ссылка'})
    elif 'Unnamed: 13' in df.columns and 'Предмет' not in df.columns: df = df.rename(columns={'Unnamed: 13': 'Предмет'})
        
    if 'Фото_ссылка' not in df.columns: df['Фото_ссылка'] = None
    if 'Бренд' not in df.columns: df['Бренд'] = 'Не указан'
    if 'Цена' not in df.columns: df['Цена'] = 0
    if 'Предмет' not in df.columns: df['Предмет'] = 'Не указан'
        
    df['Период'] = pd.to_datetime(df['Период'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Период'])
    df['SKU'] = df['SKU'].astype(str).str.replace('.0', '', regex=False)
    
    numeric_cols = ['Показы', 'Клики', 'Корзины', 'Заказы_шт', 'Заказы_руб', 'Выкупы_шт', 'Выкупы_руб', 'Цена']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'\s+', '', regex=True), errors='coerce').fillna(0)
            
    # Заполняем пустые предметы и бренды, чтобы фильтры не ломались
    df['Предмет'] = df['Предмет'].fillna('Не указан')
    df['Бренд'] = df['Бренд'].fillna('Не указан')
    return df

df = load_data()
df_sizes = load_sizes_data()
all_skus = df['SKU'].unique().tolist()

if not st.session_state.global_sku and all_skus:
    st.session_state.global_sku = all_skus[0]

st.title("📊 Аналитика продаж")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("Панель управления")
max_date_global = df['Период'].max()
min_date_global = df['Период'].min()

st.sidebar.subheader("Период анализа")
period_type = st.sidebar.radio(
    "Выберите интервал дат:",
    ("За всё время", "Последняя неделя", "Последний месяц", "Последние 3 месяца", "Последние 6 месяцев", "За год", "Произвольный период")
)

start_date = min_date_global
end_date = max_date_global

if period_type == "Последняя неделя": start_date = max_date_global - pd.DateOffset(weeks=1)
elif period_type == "Последний месяц": start_date = max_date_global - pd.DateOffset(months=1)
elif period_type == "Последние 3 месяца": start_date = max_date_global - pd.DateOffset(months=3)
elif period_type == "Последние 6 месяцев": start_date = max_date_global - pd.DateOffset(months=6)
elif period_type == "За год": start_date = max_date_global - pd.DateOffset(years=1)
elif period_type == "Произвольный период":
    dates = st.sidebar.date_input("Укажите диапазон дат", value=(min_date_global.date(), max_date_global.date()), min_value=min_date_global.date(), max_value=max_date_global.date())
    if len(dates) == 2: start_date, end_date = pd.to_datetime(dates[0]), pd.to_datetime(dates[1])
    else: start_date = end_date = pd.to_datetime(dates[0])

df_filtered_dates = df[(df['Период'] >= start_date) & (df['Период'] <= end_date)]

# --- НАВИГАЦИЯ ---
selected_tab = st.radio("Меню", tabs_list, index=tabs_list.index(st.session_state.current_tab), horizontal=True, label_visibility="collapsed")
if selected_tab != st.session_state.current_tab:
    st.session_state.current_tab = selected_tab
    st.rerun()

st.divider()

# ==========================================
# ЭКРАН 0: КАТАЛОГ ТОВАРОВ
# ==========================================
if st.session_state.current_tab == "🛒 Каталог товаров":
    st.markdown("### Каталог отслеживаемых товаров")
    
    # Уникальная база для каталога
    catalog_df = df[['SKU', 'Фото_ссылка', 'Бренд', 'Предмет']].dropna(subset=['SKU']).drop_duplicates(subset=['SKU'])
    
    # БЛОК ФИЛЬТРОВ
    st.markdown("#### 🎛 Фильтрация каталога")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        brands_list = sorted(catalog_df['Бренд'].astype(str).unique())
        selected_brands = st.multiselect("Выберите Бренд:", brands_list, placeholder="Все бренды")
    with f_col2:
        subjects_list = sorted(catalog_df['Предмет'].astype(str).unique())
        selected_subjects = st.multiselect("Выберите Предмет:", subjects_list, placeholder="Все предметы")
        
    # Применение фильтров
    if selected_brands:
        catalog_df = catalog_df[catalog_df['Бренд'].isin(selected_brands)]
    if selected_subjects:
        catalog_df = catalog_df[catalog_df['Предмет'].isin(selected_subjects)]
        
    st.info(f"Отображено товаров: **{len(catalog_df)}**")
    st.divider()

    # ВЫВОД ТОВАРОВ
    cols = st.columns(5)
    for i, (idx, row) in enumerate(catalog_df.iterrows()):
        with cols[i % 5]:
            st.markdown(f"**{row['Бренд']}**<br><span style='font-size: 12px; color: gray;'>{row['Предмет']}</span>", unsafe_allow_html=True)
            img_url = row['Фото_ссылка'] if pd.notna(row['Фото_ссылка']) else "https://via.placeholder.com/150?text=No+Photo"
            st.image(img_url, use_container_width=True)
            st.caption(f"Артикул: {row['SKU']}")
            if st.button("📊 Анализировать", key=f"cat_btn_{row['SKU']}", use_container_width=True):
                st.session_state.global_sku = row['SKU']
                st.session_state.current_tab = "📈 Динамика товара (История)"
                st.rerun()

# ==========================================
# ЭКРАН 1: ДИНАМИКА ТОВАРА
# ==========================================
elif st.session_state.current_tab == "📈 Динамика товара (История)":
    st.markdown("### Выбор товара")
    col_input1, col_input2 = st.columns(2)
    with col_input1: sku_input_method = st.radio("Как найти артикул?", ("Выбрать из списка", "Вставить вручную"), horizontal=True)
    
    selected_sku = None
    with col_input2:
        if sku_input_method == "Вставить вручную":
            raw_sku = st.text_input("Введите артикул:", value=st.session_state.global_sku)
            if raw_sku:
                if raw_sku.strip() in all_skus: selected_sku = raw_sku.strip(); st.session_state.global_sku = selected_sku
                else: st.error("❌ Артикула нет в базе.")
        else:
            default_idx = all_skus.index(st.session_state.global_sku) if st.session_state.global_sku in all_skus else 0
            selected_sku = st.selectbox("Выберите артикул:", all_skus, index=default_idx)
            st.session_state.global_sku = selected_sku
    
    st.divider()

    if selected_sku:
        sku_df = df_filtered_dates[df_filtered_dates['SKU'] == selected_sku]
        
        # --- БЛОК ОСНОВНЫХ МЕТРИК ---
        st.markdown("### 📊 Основные показатели за выбранный период")
        if not sku_df.empty:
            total_orders = sku_df['Заказы_шт'].sum()
            total_orders_rub = sku_df['Заказы_руб'].sum()
            total_buyouts = sku_df['Выкупы_шт'].sum()
            total_sales_rub = sku_df['Выкупы_руб'].sum()
            
            avg_price = sku_df[sku_df['Цена'] > 0]['Цена'].mean() if not sku_df.empty else 0
            if pd.isna(avg_price): avg_price = 0

            # Разбиваем на 4 колонки
            m_col_img, m_col1, m_col2, m_col3 = st.columns([1, 1.5, 1.5, 1.5])
            
            with m_col_img:
                if 'Фото_ссылка' in sku_df.columns and pd.notna(sku_df['Фото_ссылка'].iloc[0]):
                    st.image(sku_df['Фото_ссылка'].iloc[0], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/150?text=No+Photo", use_container_width=True)
                    
            with m_col1: 
                st.metric("Артикул", selected_sku)
                st.metric("Ср. Цена", f"{format_number(avg_price)} ₽")
            with m_col2: 
                st.metric("Заказы (шт)", format_number(total_orders))
                st.metric("Заказы (руб)", f"{format_number(total_orders_rub)} ₽")
            with m_col3: 
                st.metric("Выкупы (шт)", format_number(total_buyouts))
                st.metric("Выручка (руб)", f"{format_number(total_sales_rub)} ₽")
        else:
            st.warning("В выбранном периоде нет данных по этому товару. Расширьте диапазон дат в левом меню.")
        
        st.divider()

        # --- БЛОК ГРАФИКОВ И ДЕТАЛЬНОЙ ТАБЛИЦЫ ---
        st.markdown("### 📈 Графики продаж")
        grouping = st.radio("Группировка данных:", ("По месяцам", "По неделям"), horizontal=True)

        if not sku_df.empty:
            display_df = sku_df.copy()
            
            # Подготовка дат для группировки
            if grouping == "По неделям":
                display_df['Sort_Date'] = display_df['Период'] - pd.to_timedelta(display_df['Период'].dt.dayofweek, unit='d')
                display_df['Ось_Времени'] = display_df['Sort_Date'].dt.strftime('%d.%m') + "-" + (display_df['Sort_Date'] + pd.Timedelta(days=6)).dt.strftime('%d.%m.%Y')
                display_df['Sort_Num'] = display_df['Sort_Date'].dt.strftime('%Y%m%d').astype(int)
            else:
                display_df['Sort_Date'] = display_df['Период'].dt.to_period('M').dt.to_timestamp()
                display_df['Ось_Времени'] = display_df['Sort_Date'].apply(lambda x: f"{MONTHS_RU[x.month]} {x.year}" if pd.notnull(x) else "")
                display_df['Sort_Num'] = display_df['Sort_Date'].dt.strftime('%Y%m').astype(int)

            # --- ГРАФИК ---
            grouped_df_chart = display_df.groupby(['Sort_Num', 'Ось_Времени'], as_index=False).agg({'Заказы_шт': 'sum', 'Выкупы_шт': 'sum'})
            grouped_df_chart = grouped_df_chart.sort_values('Sort_Num')
            
            chart_df = grouped_df_chart.rename(columns={'Заказы_шт': 'Заказы', 'Выкупы_шт': 'Выкупы'})
            base = alt.Chart(chart_df).encode(x=alt.X('Ось_Времени:O', sort=alt.EncodingSortField(field='Sort_Num'), axis=alt.Axis(labelAngle=-45)))
            lines = base.transform_fold(['Заказы', 'Выкупы'], as_=['Показатель', 'Значение']).mark_line(point=True).encode(
                y='Значение:Q', color=alt.Color('Показатель:N', scale=alt.Scale(range=['#0b57d0', '#d85900']))
            )
            st.altair_chart(lines, use_container_width=True)

            # --- ДЕТАЛЬНАЯ ТАБЛИЦА ПО ПЕРИОДАМ ---
            st.markdown("### 📋 Детализация показателей")
            
            # Чтобы нули не портили среднюю цену
            display_df['Цена_non_zero'] = display_df['Цена'].replace(0, pd.NA)

            detailed_grouped = display_df.groupby(['Sort_Num', 'Ось_Времени'], as_index=False).agg({
                'Показы': 'sum',
                'Клики': 'sum',
                'Корзины': 'sum',
                'Заказы_шт': 'sum',
                'Заказы_руб': 'sum',
                'Выкупы_шт': 'sum',
                'Выкупы_руб': 'sum',
                'Цена_non_zero': 'mean'
            }).sort_values('Sort_Num')

            detailed_grouped['Цена_non_zero'] = detailed_grouped['Цена_non_zero'].fillna(0)

            # Переименовываем для красоты
            detailed_display = detailed_grouped.rename(columns={
                'Ось_Времени': 'Период',
                'Цена_non_zero': 'Ср. Цена',
                'Заказы_шт': 'Заказы (шт)',
                'Заказы_руб': 'Заказы (руб)',
                'Выкупы_шт': 'Выкупы (шт)',
                'Выкупы_руб': 'Выручка (руб)'
            })

            # Форматируем столбцы: добавляем пробелы и знаки рубля
            detailed_display = detailed_display.astype(object)

            for col in ['Заказы (руб)', 'Выручка (руб)', 'Ср. Цена']:
                detailed_display[col] = detailed_display[col].apply(lambda x: f"{format_number(x)} ₽" if pd.notna(x) and x > 0 else "0 ₽")

            for col in ['Показы', 'Клики', 'Корзины', 'Заказы (шт)', 'Выкупы (шт)']:
                detailed_display[col] = detailed_display[col].apply(lambda x: format_number(x) if pd.notna(x) else "0")

            # Выводим таблицу
            st.dataframe(
                detailed_display[['Период', 'Показы', 'Клики', 'Корзины', 'Заказы (шт)', 'Заказы (руб)', 'Выкупы (шт)', 'Выручка (руб)', 'Ср. Цена']],
                hide_index=True,
                use_container_width=True
            )

            # --- РАЗМЕРЫ ---
            st.markdown("### 📏 Продажи по размерам")
            if not df_sizes.empty and 'SKU' in df_sizes.columns:
                sku_sizes = df_sizes[df_sizes['SKU'] == selected_sku].copy()
                if not sku_sizes.empty:
                    display_sizes = sku_sizes.groupby('Размер', as_index=False).agg({'Корзины':'sum', 'Заказы':'sum', 'Выкупы':'sum'})
                    
                    total_orders_for_sizes = display_sizes['Заказы'].sum()
                    total_buyouts_for_sizes = display_sizes['Выкупы'].sum()
                    
                    if total_orders_for_sizes > 0:
                        display_sizes['Доля заказов (%)'] = (display_sizes['Заказы'] / total_orders_for_sizes * 100).fillna(0).round(1).apply(lambda x: f"{x}%")
                    else:
                        display_sizes['Доля заказов (%)'] = "0%"
                        
                    if total_buyouts_for_sizes > 0:
                        display_sizes['Доля выкупов (%)'] = (display_sizes['Выкупы'] / total_buyouts_for_sizes * 100).fillna(0).round(1).apply(lambda x: f"{x}%")
                    else:
                        display_sizes['Доля выкупов (%)'] = "0%"
                        
                    st.dataframe(display_sizes, hide_index=True, use_container_width=True)

# ==========================================
# ЭКРАН 2: СРАВНЕНИЕ КОНКУРЕНТОВ (РЫНОК)
# ==========================================
elif st.session_state.current_tab == "⚔️ Сравнение конкурентов (Рынок)":
    st.markdown("### Анализ рынка и конкурентов")
    st.info(f"📅 Данные отображаются за период: **{start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}**")
    
    grouping_comp = st.radio("Детализация таблицы:", ("За весь выбранный период", "По месяцам", "По неделям"), horizontal=True)
    st.divider()
    
    my_sku = st.text_input("💎 Мой артикул:", value=st.session_state.global_sku)
    col_comp1, col_comp2 = st.columns(2)
    with col_comp1:
        comp_manual = st.text_area("✍️ Ввести артикулы конкурентов (через запятую или пробел):", placeholder="Например: 123456, 7891011")
    with col_comp2:
        competitors_sel = st.multiselect("⚔️ Или выбрать из базы:", all_skus)

    # Собираем все артикулы вместе
    skus_to_compare = []
    if my_sku: skus_to_compare.append(my_sku)
    
    comp_list = []
    if comp_manual:
        import re
        parsed_skus = re.findall(r'\d+', comp_manual)
        comp_list.extend(parsed_skus)
    if competitors_sel:
        comp_list.extend(competitors_sel)
        
    comp_list = list(set(comp_list)) 
    if my_sku in comp_list: comp_list.remove(my_sku)
    skus_to_compare.extend(comp_list)

    if len(skus_to_compare) > 0:
        comp_data = df_filtered_dates[df_filtered_dates['SKU'].isin(skus_to_compare)].copy()
        
        if not comp_data.empty:
            groupby_cols = []
            if grouping_comp == "По неделям":
                comp_data['Sort_Date'] = comp_data['Период'] - pd.to_timedelta(comp_data['Период'].dt.dayofweek, unit='d')
                comp_data['Период_Группировки'] = comp_data['Sort_Date'].dt.strftime('%d.%m') + "-" + (comp_data['Sort_Date'] + pd.Timedelta(days=6)).dt.strftime('%d.%m.%Y')
                comp_data['Sort_Num'] = comp_data['Sort_Date'].dt.strftime('%Y%m%d').astype(int)
                groupby_cols = ['Sort_Num', 'Период_Группировки', 'SKU']
            elif grouping_comp == "По месяцам":
                comp_data['Sort_Date'] = comp_data['Период'].dt.to_period('M').dt.to_timestamp()
                comp_data['Период_Группировки'] = comp_data['Sort_Date'].apply(lambda x: f"{MONTHS_RU[x.month]} {x.year}" if pd.notnull(x) else "")
                comp_data['Sort_Num'] = comp_data['Sort_Date'].dt.strftime('%Y%m').astype(int)
                groupby_cols = ['Sort_Num', 'Период_Группировки', 'SKU']
            else:
                groupby_cols = ['SKU']

            comp_data['Цена'] = comp_data['Цена'].replace(0, pd.NA)
            
            # Добавлена агрегация Заказы_руб
            comp_df = comp_data.groupby(groupby_cols, as_index=False).agg({
                'Показы': 'sum', 'Клики': 'sum', 'Корзины': 'sum', 
                'Заказы_шт': 'sum', 'Заказы_руб': 'sum', 
                'Выкупы_шт': 'sum', 'Выкупы_руб': 'sum',
                'Цена': 'mean'
            })
            
            comp_df['Цена'] = comp_df['Цена'].fillna(0)

            brand_df = df[['SKU', 'Бренд', 'Фото_ссылка']].dropna(subset=['SKU']).drop_duplicates(subset=['SKU'])
            comp_df = comp_df.merge(brand_df, on='SKU', how='left')
            comp_df['Бренд'] = comp_df['Бренд'].fillna("Не указан")
            
            comp_df['SKU_clean'] = comp_df['SKU']
            comp_df['SKU'] = comp_df['SKU'] + " (" + comp_df['Бренд'] + ")"
            comp_df = comp_df.rename(columns={'Фото_ссылка': 'Фото'})
            if grouping_comp != "За весь выбранный период":
                comp_df = comp_df.rename(columns={'Период_Группировки': 'Период'})

            comp_df['CTR (%)'] = (comp_df['Клики'] / comp_df['Показы'] * 100).round(2)
            comp_df['В Корзину (%)'] = (comp_df['Корзины'] / comp_df['Клики'] * 100).round(2)
            comp_df['В Заказ (%)'] = (comp_df['Заказы_шт'] / comp_df['Корзины'] * 100).round(2)
            
            # Переименовываем столбцы для итоговой таблицы
            comp_df = comp_df.rename(columns={
                'Заказы_шт': 'Заказы (шт)',
                'Заказы_руб': 'Заказы (руб)',
                'Выкупы_шт': 'Выкупы (шт)',
                'Выкупы_руб': 'Выручка (руб)', 
                'Цена': 'Ср. Цена (руб)'
            })

            # Сортировка: Мой товар всегда сверху
            comp_df['Is_Mine'] = comp_df['SKU_clean'] == my_sku
            if grouping_comp == "За весь выбранный период":
                comp_df = comp_df.sort_values(by=['Is_Mine', 'Выручка (руб)'], ascending=[False, False]).reset_index(drop=True)
            else:
                comp_df = comp_df.sort_values(by=['Sort_Num', 'Is_Mine', 'Выручка (руб)'], ascending=[True, False, False]).reset_index(drop=True)

            # Определяем порядок столбцов в таблице с новым полем "Заказы (руб)"
            numeric_columns = ['Ср. Цена (руб)', 'Показы', 'Клики', 'Корзины', 'Заказы (шт)', 'Заказы (руб)', 'Выкупы (шт)', 'Выручка (руб)', 'CTR (%)', 'В Корзину (%)', 'В Заказ (%)']

            if grouping_comp != "За весь выбранный период":
                max_vals = comp_df.groupby('Период')[numeric_columns].transform('max')
                min_vals = comp_df.groupby('Период')[numeric_columns].transform('min')
            else:
                max_vals = pd.DataFrame([comp_df[numeric_columns].max()] * len(comp_df), index=comp_df.index)
                min_vals = pd.DataFrame([comp_df[numeric_columns].min()] * len(comp_df), index=comp_df.index)

            css_df = pd.DataFrame('', index=comp_df.index, columns=comp_df.columns)
            
            # Приводим к типу object, чтобы Pandas разрешил вставлять форматированные строки со знаками ₽
            display_df = comp_df.astype(object).copy()

            for i, row in comp_df.iterrows():
                is_mine = row['Is_Mine']
                
                if is_mine:
                    css_df.loc[i, :] = 'border-bottom: 3px solid #cb11ab; background-color: rgba(203, 17, 171, 0.05); font-weight: bold;'
                    
                for col in numeric_columns:
                    val = row[col]
                    leader_val = max_vals.loc[i, col]
                    worst_val = min_vals.loc[i, col]
                    
                    if pd.isna(val): formatted_val = ""
                    elif col in ['CTR (%)', 'В Корзину (%)', 'В Заказ (%)']: formatted_val = f"{val:.2f}%"
                    elif col in ['Ср. Цена (руб)', 'Заказы (руб)', 'Выручка (руб)']: formatted_val = f"{format_number(val)} ₽"
                    else: formatted_val = format_number(val)
                        
                    if pd.notna(val) and val == leader_val and leader_val > 0:
                        css_df.loc[i, col] += 'background-color: rgba(40, 167, 69, 0.3);'
                    elif pd.notna(val) and val == worst_val and comp_df[col].nunique() > 1:
                        css_df.loc[i, col] += 'background-color: rgba(220, 53, 69, 0.3);'
                        
                    if is_mine and pd.notna(val) and pd.notna(leader_val) and leader_val > 0:
                        if val < leader_val:
                            diff = ((leader_val - val) / leader_val) * 100
                            formatted_val += f" (🔻 -{diff:.1f}%)"
                        elif val == leader_val:
                            formatted_val += " (👑)"
                            
                    display_df.at[i, col] = formatted_val

            cols_to_drop = ['Is_Mine', 'SKU_clean', 'Бренд', 'Sort_Num', 'Sort_Date']
            display_df = display_df.drop(columns=[c for c in cols_to_drop if c in display_df.columns])
            css_df = css_df.drop(columns=[c for c in cols_to_drop if c in css_df.columns])

            if 'Период' in display_df.columns: cols = ['Период', 'SKU', 'Фото'] + [c for c in display_df.columns if c not in ['Период', 'SKU', 'Фото']]
            else: cols = ['SKU', 'Фото'] + [c for c in display_df.columns if c not in ['SKU', 'Фото']]
            
            display_df = display_df[cols]
            css_df = css_df[cols]

            def apply_css(x): return css_df
            styled_df = display_df.style.apply(apply_css, axis=None)

            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                column_config={"Фото": st.column_config.ImageColumn("Фото", help="Превью", width="small")}
            )
        else:
            st.info("В выбранном периоде нет данных по этим артикулам.")
    else:
        st.info("Укажите свой артикул и конкурентов для сравнения.")
