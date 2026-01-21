import streamlit as st
import pandas as pd
import re
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Twinning Partner Finder", layout="wide", page_icon="🌍")

# --- SABİT ÜLKE LİSTESİ (Manuel Seçim İçin) ---
WORLD_COUNTRIES = sorted([
    "United States", "China", "United Kingdom", "Germany", "India", "Japan", "France", "Italy", "Canada", "Australia",
    "Spain", "South Korea", "Brazil", "Russia", "Netherlands", "Iran", "Turkey", "Switzerland", "Poland", "Sweden",
    "Taiwan", "Belgium", "Malaysia", "Denmark", "Portugal", "Mexico", "South Africa", "Austria", "Egypt", "Czech Republic",
    "Israel", "Finland", "Norway", "Greece", "Singapore", "Pakistan", "Thailand", "Saudi Arabia", "Ireland", "Romania",
    "New Zealand", "Argentina", "Chile", "Ukraine", "Hungary", "Colombia", "Nigeria", "Vietnam", "Indonesia", "Slovakia",
    "Croatia", "Slovenia", "Lithuania", "Estonia", "Latvia", "Serbia", "Bulgaria", "Philippines", "Morocco", "Iraq",
    "Tunisia", "Algeria", "Bangladesh", "Jordan", "Kuwait", "Lebanon", "Qatar", "United Arab Emirates", "Kazakhstan"
])

# --- YARDIMCI FONKSİYONLAR ---
def parse_correspondence(corr_str):
    if not isinstance(corr_str, str): return {'emails': [], 'p_name': ''}
    # Email regex
    emails = re.findall(r'email:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', corr_str)
    # İlk kısım genelde isimdir
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

def process_data(df, filter_mode, selected_countries):
    extracted_data = []
    
    # İlerleme çubuğu
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_rows = len(df)
    
    for index, row in df.iterrows():
        # Görsel güncelleme (her 50 satırda bir)
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
            
            # --- FİLTRELEME MANTIĞI BURADA ---
            should_include = False
            
            if filter_mode == "Tüm Dünyayı Getir (TR Dahil)":
                should_include = True
            
            elif filter_mode == "Tüm Dünyayı Getir (TR Hariç)":
                # Turkey veya Turkiye değilse al
                if country.lower() not in ["turkey", "türkiye", "turkiye"]:
                    should_include = True
                    
            elif filter_mode == "Manuel Ülke Seçimi":
                if country in selected_countries:
                    should_include = True
            
            # Eğer filtreyi geçtiyse E-posta kontrolü yap
            if should_include:
                email = match_email(author_name, corr_info, str(corr_str))
                
                if email:
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
        worksheet.set_column('A:A', 25) # İsim
        worksheet.set_column('B:B', 30) # Email
        worksheet.set_column('C:C', 15) # Ülke
        worksheet.set_column('D:D', 50) # Kurum
        worksheet.set_column('E:E', 40) # Başlık
    processed_data = output.getvalue()
    return processed_data

# --- ARAYÜZ TASARIMI ---

st.title("🌍 Scopus Twinning Partner Bulucu")
st.markdown("Scopus verilerinden yazar ve e-posta ayıklama aracı. Ülke bazlı filtreleme yapabilirsiniz.")

# --- SIDEBAR (SOL MENÜ) AYARLARI ---
st.sidebar.header("⚙️ Filtre Ayarları")

# 1. Filtre Modu Seçimi
filter_option = st.sidebar.radio(
    "Hangi ülkeleri istiyorsunuz?",
    ("Tüm Dünyayı Getir (TR Dahil)", 
     "Tüm Dünyayı Getir (TR Hariç)", 
     "Manuel Ülke Seçimi")
)

selected_countries_list = []

# 2. Eğer Manuel Seçim yapıldıysa listeyi göster
if filter_option == "Manuel Ülke Seçimi":
    st.sidebar.markdown("---")
    container = st.sidebar.container()
    all_selected = st.sidebar.checkbox("Listedeki Tümünü Seç", value=False)
    
    if all_selected:
        selected_countries_list = container.multiselect(
            "Ülkeleri Seçin:",
            WORLD_COUNTRIES,
            default=WORLD_COUNTRIES
        )
    else:
        # Varsayılan olarak boş veya birkaç popüler ülke seçili gelebilir
        selected_countries_list = container.multiselect(
            "Ülkeleri Seçin:",
            WORLD_COUNTRIES,
            default=["United Kingdom", "Germany", "France", "Italy", "Spain"]
        )

# --- KULLANIM KILAVUZU ---
with st.expander("ℹ️ Scopus'tan Dosya Nasıl İndirilir? (Rehber)", expanded=False):
    st.markdown("""
    1. **Scopus'a Giriş Yapın:** [Scopus.com](https://www.scopus.com)
    2. **Arama Yapın:** Anahtar kelimenizi ve yılları (örn: 2024-2027) girin.
    3. **Tümünü Seçin:** Tablonun üstündeki `All` kutucuğunu işaretleyin.
    4. **Dışa Aktar (Export):** * Format: **CSV**
       * Mutlaka seçin: **Other information** (E-postalar burada), **Authors with affiliations**, **Bibliographical information**.
    5. **İndirin** ve buraya yükleyin.
    """)

# --- DOSYA YÜKLEME ALANI ---
uploaded_file = st.file_uploader("📂 Scopus CSV dosyasını buraya sürükleyin", type=['csv'])

if uploaded_file is not None:
    # Veriyi oku
    try:
        df = pd.read_csv(uploaded_file)
        
        # Sütun Kontrolü
        if 'Authors with affiliations' not in df.columns:
            st.error("❌ Dosyada 'Authors with affiliations' sütunu yok. Yanlış dosya formatı.")
        elif 'Correspondence Address' not in df.columns:
            st.error("❌ Dosyada 'Correspondence Address' sütunu yok. E-postalar çekilemez. Lütfen 'Other information' seçerek indirin.")
        else:
            st.info(f"Dosya yüklendi. Seçilen Mod: **{filter_option}**")
            
            # İşleme Başla Butonu (İsteğe bağlı, otomatik de olabilir ama buton daha kontrollü)
            if st.button("🚀 Analizi Başlat"):
                
                result_df = process_data(df, filter_option, selected_countries_list)
                
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
        st.error(f"Dosya okunurken hata oluştu: {e}")

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
