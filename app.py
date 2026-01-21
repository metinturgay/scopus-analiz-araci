import streamlit as st
import pandas as pd
import re
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Twinning Partner Finder", layout="wide", page_icon="🌍")

# --- 1. SABİT LİSTELER ---

# Twinning Ülkeleri (Sabit Liste)
TWINNING_COUNTRIES = [
    "Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Iceland", "Ireland", "Italy",
    "Luxembourg", "Netherlands", "Norway", "Spain", "Sweden", "Switzerland", "United Kingdom", "UK"
]

# Tüm Dünya Ülkeleri (Genişletilmiş Liste)
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
def parse_correspondence(corr_str):
    if not isinstance(corr_str, str): return {'emails': [], 'p_name': ''}
    emails = re.findall(r'email:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', corr_str)
    p_name = corr_str.split(';')[0].strip()
    return {'emails': emails, 'primary_name': p_name}

def match_email(author_name, corr_info, corr_str_full):
    if not corr_info['emails']: return None
    parts = author_name.split(', ')
    surname = parts[0].strip()
    
    # Sorumlu yazar kontrolü
    if surname.lower() in corr_info['primary_name'].lower():
        return corr_info['emails'][0]
    # Tek mail varsa ve soyadı metinde geçiyorsa
    if len(corr_info['emails']) == 1 and surname in corr_str_full:
        return corr_info['emails'][0]
    return None

def process_data(df, filter_mode, selected_countries, custom_countries_input):
    extracted_data = []
    
    # İlerleme çubuğu
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_rows = len(df)
    
    # Manuel girişleri listeye ekle (virgülle ayrılmışsa böl ve temizle)
    manual_country_list = []
    if custom_countries_input:
        manual_country_list = [c.strip() for c in custom_countries_input.split(',') if c.strip()]
    
    # Seçili ülkeler + Manuel girilenler
    final_selected_countries = set(selected_countries + manual_country_list)

    for index, row in df.iterrows():
        if index % 50 == 0:
            progress_bar.progress(min(index / total_rows, 1.0))
            status_text.text(f"Taranıyor: {index}/{total_rows} satır...")

        auth_affil_str = row.get('Authors with affiliations', '')
        corr_str = row.get('Correspondence Address', '')
        paper_title = row.get('Title', '')
        year = row.get('Year', '')
        
        if pd.isna(auth_affil_str): continue
            
        corr_info = parse_correspondence(corr_str)
        authors_list = auth_affil_str.split('; ')
        
        for auth_entry in authors_list:
            parts = auth_entry.split(', ')
            
            if len(parts) >= 3:
                author_name = f"{parts[0]}, {parts[1]}"
                affiliation = ", ".join(parts[2:])
                country = parts[-1].strip().replace('.', '')
            else:
                author_name = auth_entry
                affiliation = ""
                country = ""
            
            country = country.strip()
            
            # Önce Email'i bul (TR kontrolü için gerekli)
            email = match_email(author_name, corr_info, str(corr_str))
            
            # Eğer email yoksa zaten ekleyemeyiz, sonraki kişiye geç
            if not email:
                continue

            # --- FİLTRELEME MANTIĞI ---
            should_include = False
            
            # 1. Sadece Twinning Ülkeleri
            if filter_mode == "Sadece Twinning Ülkeleri":
                if country in TWINNING_COUNTRIES:
                    should_include = True
            
            # 2. Tüm Dünya (TR Dahil) - Hiçbir filtre yok, herkes gelir
            elif filter_mode == "Tüm Dünyayı Getir (TR Dahil)":
                should_include = True
            
            # 3. TR Hariç (Ülke Adı VE .edu.tr kontrolü)
            elif filter_mode == "Tüm Dünyayı Getir (TR Hariç)":
                is_tr_country = country.lower() in ["turkey", "türkiye", "turkiye"]
                is_tr_email = ".edu.tr" in email.lower() # Email içinde .edu.tr var mı?
                
                # Hem ülke TR değil, hem de mail .edu.tr değilse ekle
                if not is_tr_country and not is_tr_email:
                    should_include = True
                    
            # 4. Manuel Seçim (Liste + Elle Yazılanlar)
            elif filter_mode == "Manuel Ülke Seçimi":
                # Scopus bazen ülke isimlerini farklı yazabilir, o yüzden tam eşleşme arıyoruz
                if country in final_selected_countries:
                    should_include = True
            
            # Karar olumluysa listeye ekle
            if should_include:
                extracted_data.append({
                    'Yazar Adı': author_name,
                    'Yazar E-postası': email,
                    'Ülke': country,
                    'Kurum': affiliation,
                    'Makale Başlığı': paper_title,
                    'Yıl': year
                })
    
    progress_bar.progress(1.0)
    status_text.empty()
    return pd.DataFrame(extracted_data)

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
    processed_data = output.getvalue()
    return processed_data

# --- ARAYÜZ TASARIMI ---

st.title("🌍 Scopus Twinning Partner Bulucu")
st.markdown("Scopus verilerinden yazar ve e-posta ayıklama aracı.")

# --- SIDEBAR (SOL MENÜ) ---
st.sidebar.header("⚙️ Filtre Ayarları")

# RADYO BUTONU
filter_option = st.sidebar.radio(
    "Hangi ülkeleri istiyorsunuz?",
    ("Sadece Twinning Ülkeleri", 
     "Tüm Dünyayı Getir (TR Dahil)", 
     "Tüm Dünyayı Getir (TR Hariç)", 
     "Manuel Ülke Seçimi")
)

selected_countries_list = []
custom_countries_text = ""

# Eğer Manuel Seçim ise
if filter_option == "Manuel Ülke Seçimi":
    st.sidebar.markdown("---")
    container = st.sidebar.container()
    
    # 1. Hazır Listeden Seçim
    all_selected = st.sidebar.checkbox("Listedeki Tümünü Seç", value=False)
    if all_selected:
        selected_countries_list = container.multiselect("Ülkeleri Seçin:", ALL_COUNTRIES_LIST, default=ALL_COUNTRIES_LIST)
    else:
        selected_countries_list = container.multiselect("Ülkeleri Seçin:", ALL_COUNTRIES_LIST, default=["United Kingdom", "Germany", "France"])
    
    # 2. Manuel Metin Girişi (Yeni Özellik)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**➕ Listede Olmayan Ülkeler:**")
    custom_countries_text = st.sidebar.text_input(
        "Ülke isimlerini virgülle ayırarak yazın:",
        placeholder="Örn: USSR, West Germany..."
    )

# Bilgi Notları
if filter_option == "Sadece Twinning Ülkeleri":
    st.sidebar.info(f"Seçili Twinning Ülkeleri:\n{', '.join(TWINNING_COUNTRIES)}")
elif filter_option == "Tüm Dünyayı Getir (TR Hariç)":
    st.sidebar.warning("⚠️ Türkiye (Turkey/Turkiye) ve '.edu.tr' uzantılı e-postalar filtrelenecektir.")

# --- REHBER ---
with st.expander("ℹ️ Scopus'tan Dosya Nasıl İndirilir? (Rehber)", expanded=False):
    st.markdown("""
    1. **Scopus'a Giriş Yapın:** [Scopus.com](https://www.scopus.com)
    2. **Arama Yapın:** Anahtar kelimenizi ve yılları (örn: 2024-2027) girin.
    3. **Tümünü Seçin:** Tablonun üstündeki `All` kutucuğunu işaretleyin.
    4. **Dışa Aktar (Export):** * Format: **CSV**
       * Mutlaka seçin: **Other information**, **Authors with affiliations**, **Bibliographical information**.
    5. **İndirin** ve buraya yükleyin.
    """)

# --- DOSYA YÜKLEME ---
uploaded_file = st.file_uploader("📂 Scopus CSV dosyasını buraya sürükleyin", type=['csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        if 'Authors with affiliations' not in df.columns or 'Correspondence Address' not in df.columns:
            st.error("❌ Dosya formatı hatalı. Lütfen 'Authors with affiliations' ve 'Correspondence Address' sütunlarının olduğundan emin olun.")
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
        st.error(f"Hata: {e}")

# --- FOOTER ---
st.markdown("""
    <style>
        .footer {text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px;}
        .footer a {color: #e44d26; text-decoration: none; font-weight: bold;}
    </style>
    <div class="footer">
        Made with ❤️ by <a href="https://metinturgay.net" target="_blank">Metin Turgay</a>
    </div>
    """, unsafe_allow_html=True)

