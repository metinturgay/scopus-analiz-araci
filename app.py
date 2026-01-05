import streamlit as st
import pandas as pd
import re
import io

# --- 1. AYARLAR VE LİSTELER ---
TARGET_COUNTRIES = [
    "Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Iceland", "Ireland", "Italy",
    "Luxembourg", "Netherlands", "Norway", "Spain", "Sweden", "Switzerland", "United Kingdom", "UK"
]

# --- 2. YARDIMCI FONKSİYONLAR ---
def parse_correspondence(corr_str):
    if not isinstance(corr_str, str): return {'emails': [], 'p_name': ''}
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

def process_data(df):
    extracted_data = []
    
    # İlerleme çubuğu (opsiyonel görsel)
    progress_bar = st.progress(0)
    total_rows = len(df)
    
    for index, row in df.iterrows():
        # İlerleme çubuğunu güncelle
        if index % 100 == 0:
            progress_bar.progress(min(index / total_rows, 1.0))

        auth_affil_str = row.get('Authors with affiliations', '')
        corr_str = row.get('Correspondence Address', '')
        
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
            
            # ÜLKE FİLTRESİ
            if country in TARGET_COUNTRIES:
                email = match_email(author_name, corr_info, str(corr_str))
                
                # Sadece e-postası olanları al
                if email:
                    extracted_data.append({
                        'Yazar Adı': author_name,
                        'Yazar E-postası': email,
                        'Ülke': country,
                        'Kurum': affiliation
                    })
    
    progress_bar.empty() # Çubuğu temizle
    return pd.DataFrame(extracted_data)

def to_excel(df):
    # Excel dosyasını RAM'de (hafızada) oluştur
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# --- 3. WEB ARAYÜZÜ (Streamlit) ---
st.title("Scopus Yazar ve E-posta Ayıklayıcı")
st.write("Scopus CSV dosyanızı yükleyin, sistem Avrupa (seçili ülkeler) yazarlarını ve e-postalarını sizin için ayıklasın.")

uploaded_file = st.file_uploader("Dosyayı buraya sürükleyin (CSV formatında)", type=['csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Gerekli sütunlar var mı kontrol et
        if 'Authors with affiliations' not in df.columns or 'Correspondence Address' not in df.columns:
            st.error("Hata: Dosyada 'Authors with affiliations' veya 'Correspondence Address' sütunları eksik. Lütfen doğru Scopus çıktısını yüklediğinizden emin olun.")
        else:
            st.success("Dosya yüklendi, işleniyor...")
            
            # İşlemi Başlat
            result_df = process_data(df)
            
            if not result_df.empty:
                st.write(f"**Toplam {len(result_df)} uygun yazar bulundu.**")
                st.dataframe(result_df.head()) # İlk 5 satırı göster
                
                # Excel İndirme Butonu
                excel_data = to_excel(result_df)
                st.download_button(
                    label="📥 Excel Dosyasını İndir",
                    data=excel_data,
                    file_name='filtrelenmis_yazarlar.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                st.warning("Belirtilen kriterlere uygun (e-postalı ve seçili ülkelerden) kayıt bulunamadı.")
                
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
