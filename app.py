import streamlit as st
import pandas as pd
import re
import io

# --- SAYFA AYARLARI (Geniş Görünüm) ---
st.set_page_config(page_title="Twinning Scopus Tool", layout="wide")

# --- 1. SABİTLER ---
TARGET_COUNTRIES = [
    "Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Iceland", "Ireland", "Italy",
    "Luxembourg", "Netherlands", "Norway", "Spain", "Sweden", "Switzerland", "United Kingdom", "UK"
]

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
    
    if surname.lower() in corr_info['primary_name'].lower():
        return corr_info['emails'][0]
    if len(corr_info['emails']) == 1 and surname in corr_str_full:
        return corr_info['emails'][0]
    return None

def process_data(df):
    extracted_data = []
    
    # İlerleme çubuğu
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_rows = len(df)
    
    for index, row in df.iterrows():
        if index % 50 == 0:
            progress_bar.progress(min(index / total_rows, 1.0))
            status_text.text(f"İşleniyor: {index}/{total_rows} satır...")

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
            
            if country in TARGET_COUNTRIES:
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
        # Sütun genişliklerini ayarla
        worksheet.set_column('A:A', 25) # İsim
        worksheet.set_column('B:B', 30) # Email
        worksheet.set_column('C:C', 15) # Ülke
        worksheet.set_column('D:D', 50) # Kurum
        worksheet.set_column('E:E', 40) # Başlık
    processed_data = output.getvalue()
    return processed_data

# --- 3. ARAYÜZ ---
st.title("🇪🇺 Scopus Twinning Partner Bulucu")
st.markdown("""
Bu araç, Scopus çıktısındaki makaleleri tarayarak **sadece seçili Avrupa ülkelerindeki** ve **e-posta adresi ulaşılabilir olan** araştırmacıları listeler.
""")

# --- KULLANIM KILAVUZU (Expander) ---
with st.expander("ℹ️ Scopus'tan Dosya Nasıl İndirilir? (Adım Adım)", expanded=False):
    st.markdown("""
    Doğru sonuç almak için Scopus'tan veriyi şu şekilde indirmelisiniz:
    
    1. **Scopus'a Giriş Yapın:** [Scopus.com](https://www.scopus.com) adresine giderek, kurumsal eposta şifreniz ile giriş yapın.
    2. **Arama Yapın:** `Documents` sekmesinde anahtar kelimenizi 'Article title, Abstract, Keywords' seçeneğinde aratın. 
       * *Öneri:* Filtrelerden Tarih aralığını `2025` ve sonrası seçmeniz önerilir.
    3. **Tümünü Seçin:** Sonuçlar gelince tablonun en üstündeki `All` kutucuğuna bastıktan sonra `Select all` seçeneğini işaretleyin.
    4. **Dışa Aktar (Export):** * `Export` butonuna tıklayın.
       * Format olarak **CSV** seçin.
       * **Şu bilgilerin seçili olduğundan emin olun:**
         * ✅ Citation information
         * ✅ Bibliographical information
         * ✅ Abstract & keywords
         * ✅ Indexed keywords
         * ✅ Funding details
         * ✅ **Other information**
    5. **İndir:** `Export` butonuna basıp dosyayı bilgisayarınıza indirin.
    """)

# --- DOSYA YÜKLEME ---
uploaded_file = st.file_uploader("📂 Scopus'tan indirdiğiniz CSV dosyasını buraya bırakın", type=['csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Kritik sütun kontrolü
        if 'Authors with affiliations' not in df.columns:
            st.error("❌ Hata: Dosyada 'Authors with affiliations' sütunu bulunamadı. Lütfen Scopus'tan indirirken tüm alanları seçtiğinize emin olun.")
        elif 'Correspondence Address' not in df.columns:
            st.error("❌ Hata: Dosyada 'Correspondence Address' (İletişim Adresi) sütunu yok. E-postaları bulamayız. Lütfen indirirken 'Other information' kutucuğunu işaretleyin.")
        else:
            st.success(f"✅ Dosya başarıyla yüklendi! ({len(df)} makale taranıyor...)")
            
            # İşlem
            result_df = process_data(df)
            
            if not result_df.empty:
                st.balloons()
                st.markdown(f"### 🎉 Sonuç: {len(result_df)} Potansiyel Partner Bulundu")
                
                # Önizleme
                st.dataframe(result_df.head(10))
                
                # İndirme Butonu
                excel_data = to_excel(result_df)
                st.download_button(
                    label="📥 Excel Listesini İndir",
                    data=excel_data,
                    file_name='twinning_partner_listesi.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key='download-btn'
                )
            else:
                st.warning("⚠️ Tarama bitti ancak kriterlere uygun (Seçili Avrupa ülkeleri + E-postası olan) hiç kayıt bulunamadı.")
                
    except Exception as e:
        st.error(f"Beklenmedik bir hata oluştu: {e}")

