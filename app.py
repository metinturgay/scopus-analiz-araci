import streamlit as st
import pandas as pd
import re
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Twinning Partner Finder", layout="wide", page_icon="🌍")

# --- 1. SABİT LİSTELER ---
TWINNING_COUNTRIES = [
    "Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Iceland", "Ireland", "Italy",
    "Luxembourg", "Netherlands", "Norway", "Spain", "Sweden", "Switzerland", "United Kingdom", "UK"
]

ALL_COUNTRIES_LIST = sorted([
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
    "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon",
    "Canada", "Cape Verde", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica",
    "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt",
    "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia",
    "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guyana", "Haiti", "Honduras", "Hungary",
    "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan",
    "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein",
    "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania",
    "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
    "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia",
    "Norway", "Oman", "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
    "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Samoa", "San Marino", "Saudi Arabia",
    "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia",
    "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
    "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu",
    "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
])

# --- 2. YARDIMCI FONKSİYONLAR ---
def parse_row(row, filter_mode, final_selected_countries):
    """
    Her bir veri satırını hızlıca ayrıştıran,
    Scopus'un isim/kurum dizilişindeki mantıksal hataları süzen fonksiyon.
    """
    try:
        # Hatalı veri tiplerine karşı string dönüşümü
        auth_affil_str = str(row.get('Authors with affiliations', ''))
        corr_str = str(row.get('Correspondence Address', ''))
        paper_title = str(row.get('Title', ''))
        year = str(row.get('Year', ''))

        if auth_affil_str == 'nan' or not auth_affil_str:
            return []

        # 1. E-posta Tespiti (Yedekli Regex)
        emails = re.findall(r'email:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', corr_str)
        if not emails:
            # Bazen 'email:' etiketi olmadan doğrudan yazılır
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', corr_str)
            
        p_name = corr_str.split(';')[0].strip().lower() if corr_str else ''
        corr_info = {'emails': emails, 'primary_name': p_name}

        authors_list = auth_affil_str.split('; ')
        extracted = []

        for auth_entry in authors_list:
            parts = auth_entry.split(', ')
            
            # Yazar, kurum ve ülke olarak ayrılamıyorsa format bozuktur, atla
            if len(parts) < 2:
                continue

            # 2. Doğru Endeksleme: İlk parça yazarın tam adı, son parça ülke.
            author_name = parts[0].strip()
            affiliation = ", ".join(parts[1:-1]).strip() if len(parts) > 2 else ""
            country = parts[-1].strip().replace('.', '')
            
            # 3. Soyadı Ayıklama Algoritması (Eşleştirme paradoksunu çözen kısım)
            # "Mortensen S.S." veya "Mortensen S." gibi isimlerden sadece "Mortensen" kısmını alır.
            tokens = author_name.split()
            if len(tokens) > 1 and ('.' in tokens[-1] or len(tokens[-1]) == 1 or tokens[-1].isupper()):
                surname = ' '.join(tokens[:-1]).lower()
            else:
                surname = author_name.lower()

            # 4. E-posta Eşleştirme
            email = None
            if corr_info['emails']:
                if surname in corr_info['primary_name']:
                    email = corr_info['emails'][0]
                elif len(corr_info['emails']) == 1 and surname in corr_str.lower():
                    # Yazışma adresinde sadece 1 mail varsa ve soyadı adreste geçiyorsa, o mail bu yazarındır.
                    email = corr_info['emails'][0]

            if not email:
                continue

            # 5. Filtreleme Mantığı
            should_include = False
            country_lower = country.lower()

            if filter_mode == "Sadece Twinning Ülkeleri":
                if country in TWINNING_COUNTRIES:
                    should_include = True
            elif filter_mode == "Tüm Dünyayı Getir (TR Dahil)":
                should_include = True
            elif filter_mode == "Tüm Dünyayı Getir (TR Hariç)":
                is_tr_country = country_lower in ["turkey", "türkiye", "turkiye"]
                is_tr_email = ".edu.tr" in email.lower()
                if not is_tr_country and not is_tr_email:
                    should_include = True
            elif filter_mode == "Manuel Ülke Seçimi":
                if country in final_selected_countries:
                    should_include = True

            if should_include:
                extracted.append({
                    'Yazar Adı': author_name,
                    'Yazar E-postası': email,
                    'Ülke': country,
                    'Kurum': affiliation,
                    'Makale Başlığı': paper_title,
                    'Yıl': year
                })
        return extracted
    except Exception:
        # Satırda beklenmeyen, parse edilemeyen bir anormallik varsa sistemi çökertme, boş dön
        return []

def process_data(df, filter_mode, selected_countries, custom_countries_input):
    manual_country_list = [c.strip() for c in custom_countries_input.split(',') if c.strip()] if custom_countries_input else []
    final_selected_countries = set(selected_countries + manual_country_list)

    # İşlem yapılacak vektör uzayını daraltmak için sadece gerekli sütunları alıyoruz. 
    # Bu sayede RAM kullanımı ciddi oranda düşer.
    cols_needed = ['Authors with affiliations', 'Correspondence Address', 'Title', 'Year']
    available_cols = [c for c in cols_needed if c in df.columns]
    df_sub = df[available_cols]

    # Vektörel işlem: Satır satır for döngüsü yerine Pandas'ın C tabanlı apply metodunu kullanıyoruz.
    with st.spinner("Matris işleniyor, lütfen bekleyin..."):
        results_series = df_sub.apply(lambda row: parse_row(row, filter_mode, final_selected_countries), axis=1)

    # İki boyutlu listeyi tek boyuta indirge
    flat_list = [item for sublist in results_series if sublist for item in sublist]

    return pd.DataFrame(flat_list)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        worksheet = writer.sheets['Sheet1']
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 50)
        worksheet.set_column('E:E', 40)
    return output.getvalue()

# --- ARAYÜZ TASARIMI ---
st.title("🌍 Scopus Twinning Partner Bulucu")
st.markdown("Scopus verilerinden yazar ve e-posta ayıklama aracı.")

# --- SIDEBAR (SOL MENÜ) ---
st.sidebar.header("⚙️ Filtre Ayarları")

filter_option = st.sidebar.radio(
    "Hangi ülkeleri istiyorsunuz?",
    ("Tüm Dünyayı Getir (TR Dahil)", 
     "Tüm Dünyayı Getir (TR Hariç)", 
     "Sadece Twinning Ülkeleri", 
     "Manuel Ülke Seçimi")
)

selected_countries_list = []
custom_countries_text = ""

if filter_option == "Manuel Ülke Seçimi":
    st.sidebar.markdown("---")
    container = st.sidebar.container()
    
    all_selected = st.sidebar.checkbox("Listedeki Tümünü Seç", value=False)
    if all_selected:
        selected_countries_list = container.multiselect("Ülkeleri Seçin:", ALL_COUNTRIES_LIST, default=ALL_COUNTRIES_LIST)
    else:
        selected_countries_list = container.multiselect("Ülkeleri Seçin:", ALL_COUNTRIES_LIST, default=["United Kingdom", "Germany", "France"])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**➕ Listede Olmayan Ülkeler:**")
    custom_countries_text = st.sidebar.text_input(
        "Ülke isimlerini virgülle ayırarak yazın:",
        placeholder="Örn: USSR, West Germany..."
    )

if filter_option == "Sadece Twinning Ülkeleri":
    st.sidebar.info(f"Seçili Twinning Ülkeleri:\n{', '.join(TWINNING_COUNTRIES)}")
elif filter_option == "Tüm Dünyayı Getir (TR Hariç)":
    st.sidebar.warning("⚠️ Türkiye (Turkey/Turkiye) ve '.edu.tr' uzantılı e-postalar filtrelenecektir.")

with st.expander("ℹ️ Scopus'tan Dosya Nasıl İndirilir? (Adım Adım)", expanded=False):
    st.markdown("""
    1. **Scopus'a Giriş Yapın:** Scopus.com
    2. **Arama Yapın:** Documents sekmesinde anahtar kelimenizi aratın. 
    3. **Tümünü Seçin:** 'All' -> 'Select all'.
    4. **Dışa Aktar (Export):** CSV formatını seçin. Gerekli tüm bilgi sütunlarını işaretleyin.
    5. **İndir:** Export butonuna basın.
    """)

# --- DOSYA YÜKLEME ---
uploaded_file = st.file_uploader("📂 Scopus CSV dosyasını buraya sürükleyin", type=['csv'])

if uploaded_file is not None:
    try:
        # low_memory=False parametresi büyük verilerde kolon tiplerinin karışmasını engeller.
        df = pd.read_csv(uploaded_file, low_memory=False, on_bad_lines='skip')
        
        if 'Authors with affiliations' not in df.columns or 'Correspondence Address' not in df.columns:
            st.error("❌ Dosya formatı hatalı. Gerekli sütunlar eksik.")
        else:
            st.info(f"Dosya yüklendi. Mod: **{filter_option}**")
            
            if st.button("🚀 Analizi Başlat"):
                result_df = process_data(df, filter_option, selected_countries_list, custom_countries_text)
                
                if not result_df.empty:
                    st.success(f"✅ İşlem Tamamlandı! Toplam **{len(result_df)}** kişi bulundu.")
                    st.dataframe(result_df.head(10))
                    
                    excel_data = to_excel(result_df)
                    st.download_button(
                        label="📥 Excel Listesini İndir",
                        data=excel_data,
                        file_name='filtrelenmis_yazarlar.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    st.warning("⚠️ Seçilen kriterlere uygun (e-postalı) kayıt bulunamadı.")
                    
    except Exception as e:
        st.error(f"Beklenmeyen bir hata oluştu: {e}")
