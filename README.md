Script ini dibuat untuk membantu proses **analisis forensik, perbaikan zlib stream, pembacaan hex**, serta pemulihan data yang rusak.  
Tool ini bekerja otomatis membaca file, memproses byte-level data, dan menyimpan hasilnya dalam format yang telah diperbaiki.

---

##  Fitur Utama

-  Membaca file dalam format biner/hex  
-  Memperbaiki zlib stream yang rusak (raw / deflate)  
-  Mengidentifikasi pola encoding custom  
-  Output otomatis ke folder `output/`  
-  Logging proses menggunakan Rich (tampilan lebih rapi & berwarna)  

---

## 📂 Struktur Folder

```
.
├── script.py        # Script utama OPSI B
├── input/           # Masukkan file yang ingin diproses
├── output/          # Hasil pemulihan/perbaikan
├── requirements.txt # Dependency Python
└── README.md        # Dokumentasi proyek
```

---

## ⚙️ Instalasi

### 1️⃣ Clone Repository
```bash
git clone https://github.com/humanbetired/repository
cd repository
```

### 2️⃣ Install Requirements
```bash
pip install -r requirements.txt
```

---

## ▶️ Cara Menjalankan

### Mode dasar
```bash
python script.py
```

### Menjalankan dengan argumen file input
```bash
python script.py input/nama_file.bin
```

Jika script mendukung parameter tambahan, contoh:
```bash
python script.py --repair --verbose input/data.bin
```

---

##  Output

Hasil perbaikan akan otomatis tersimpan di:

```
/output/result.bin
```

Nama dan format file dapat berbeda sesuai pengaturan di dalam script.

---

##  Contoh Penggunaan

```bash
python script.py 
```

Output terminal:
```
[+] Membaca file...
[+] Mendeteksi stream...
[+] Memperbaiki zlib raw stream...
[+] Selesai! Hasil tersimpan di output/fix_data.bin
```

---

## Penjelasan Teknis (Ringkas)

Script menjalankan beberapa langkah:

1. **Load file biner** dan validasi byte panjangnya  
2. **Deteksi format & pola encoding** (zlib, deflate, custom binary)  
3. **Repair / reassemble stream** jika ditemukan data rusak  
4. **Decompress** bila memungkinkan  
5. **Simpan** hasil ke folder output  

---

## ❗ Issues

Jika menemukan bug, silakan open issue:  
https://github.com/humanbetired/repository/issues

Sertakan contoh file yang bermasalah & output error.

---

## Lisensi

Proyek ini menggunakan lisensi:

```
MIT License
```

