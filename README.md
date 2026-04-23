<div align="center">

# Disk Indeksi

**`Klasor tarayici · PyQt5 · Etiketleme & Arama`**

<br>

[![Live Demo](https://img.shields.io/badge/Canli_Demo-GitHub_Pages-1f6feb?style=for-the-badge)](https://eren-oztk.github.io/Disk_indexer/)
[![Language](https://img.shields.io/badge/Python-100%25-3776AB?style=for-the-badge&logo=python)](https://github.com/Eren-Oztk/disk-indexer)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=for-the-badge)](https://github.com/Eren-Oztk/disk-indexer)

</div>

---

**v1.0.0**

Disk ve klasörlerini taşımadan indeksle, otomatik etiketle, filtrele, bul.
Scan, auto-tag and search your folders without moving any files.

---

## Ne Yapar?

Bir klasörü seçip "Tara" dediğinde program içindeki her dosya ve alt klasörü inceler; içeriğine bakarak otomatik olarak etiket atar: kod projesi mi, kurulum aracı mı, belge mi, medya mı, arşiv mi? Etiketler `~/.disk_index.json` dosyasına kaydedilir; hiçbir dosya taşınmaz veya silinmez.

## Nasıl Calisir?

Tarama arka planda bir QThread üzerinde yürür; her klasör için `PROJECT_MARKERS` listesindeki işaretçilere (`.git`, `requirements.txt`, `package.json` vb.) bakılır. Etiket ataması dosya uzantısına ve klasör içeriğine göre yapılır. Kullanıcı sağ tıkla istediği etiketi elle değiştirebilir.

---

## Gereksinimler

| Paket | Versiyon |
|---|---|
| Python | 3.8+ |
| PyQt5 | 5.15.0+ |

---

## Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/Eren-Oztk/disk-indexer.git
cd disk-indexer

# 2. Bagimlilik kur
pip install -r requirements.txt

# 3. Calistir
python disk_indexer.py
```

**Windows (tek tik):**
```
baslat.bat
```

---

## Kullanim

1. **Klasor Sec** butonuyla taramak istedigin diski/klasörü sec (orn. `C:\` veya `D:\Projeler`)
2. **Tara** butonuna bas — otomatik etiketleme baslar
3. Yanlis etiketlenen oge icin **sag tikla → Etiket Degistir**
4. **Kaydet** ile degisiklikleri kalici hale getir

---

## Etiket Turleri

| Etiket | Kural |
|---|---|
| **Proje** | `.git`, `requirements.txt`, `package.json`, `main.py` vb. iceren klasorler |
| **Arac** | `installer`, `setup`, `.exe` / `.msi` iceren klasorler |
| **Belge** | `.pdf`, `.docx`, `.xlsx`, `.md` vb. |
| **Medya** | Resim, video, ses dosyalari |
| **Zip/Arsiv** | `.zip`, `.rar`, `.7z`, `.tar.gz` vb. |
| **Cop** | Manuel olarak isaretleyebilirsin |
| **?** | Taninamadi |

---

## Bilinen Limitasyonlar

- Tarama sadece secilen klasörün bir alt seviyesini kapsar (özyinelemeli degil)
- Sembolik linkler izlenmez
- Cok buyuk köklerde (orn. `C:\`) ilk tarama birkac saniye surebilir

---

## Lisans

MIT © 2026 Eren Öztürk
