# Tembak Web

Aplikasi berbasis python ini untuk melakukan performance test baik pada web maupun API.

## Prasyarat
- Python 3.7 (karena pakai asyncio.run yang baru ada di python3.7)
- requests (di ubuntu, bisa install dari APT php3-requests)
- commentjson (berguna untuk parsing json, bisa menyelipkan comment di config. Bisa diinstall pakai pip)
- jsonpath_ng (berguna untuk dapat data dari path. Bisa diinstall pakai pip)
- requests_oauthlib (untuk KolektorTokenOauth2)
- oauthlib (untuk KolektorTokenOauth2)
- filelock (untuk KolektorTokenOauth2)
- httpx (pengganti requests, bisa melakukan request secara paralel)

Sebagian besar prasyarat ini tersedia di pip. Jadi cukup instal <i>pip</i> dan jalankan:
<pre><code>
  pip install {nama_modul}
</code></pre>


## Penggunaan
python3 performanceTestRequest.py -c sampleConfig.json

Bisa menggunakan lebih dari satu config.

python3 performanceTestRequest.py -c sampleConfig.json -c configLain.json


Jika test terlalu dianggap lama, TembakWeb memiliki fitur membungkus proses yang diinterupsi secara kasar. 
Jadi jika anda bisa melakukan <i>Ctrl-C</i> untuk keluar dan TembakWeb akan menghitung berdasarkan test yang sudah dilakukan.


## File konfigurasi untuk Tembak Web
Isi file konfigurasi tembakWeb biasanya berupa
* version
* static-variables
* variables
* requests

### static-variables
static-variables berupa json sederhana dan saat ini belum mendukung array.
Contoh property static-variables:

<pre><code>
  "static-variable": {
    "num-of-request":1, //50,
    "num-of-concurrent-request":1, //10,
    "authorizationToken":"dummy-a-very-long-oauth-string-token"
  },
</code></pre>

Oh iya, ada variable yang harus ada minimal di salah satu file konfigurasi:
* num-of-request : jumlah request yang diinginkan
* num-of-concurrent-request: jumlah request yang akan dijalankan secara bersamaan dalam satu waktu.

### variables
variables, terinspirasi dari payload yang biasa digunakan di loader.io. Sebenarnya agak merusak format json.

<pre><code>
  "variables":[
    {  
      "names":["username","giftCard"],
      "values":[
        ["narpati@whatever.com","N0UBDVAHMGOW"],
		["kunderemp@whatever.com","N0ABCVDHMGLW"],
      ]
    }],
</code></pre>

### requests
* method: Anda bisa memilih POST atau GET. Saat ini belum mendukung PUT
* url: URL dari request yang akan anda lakukan. Anda bisa menyelipkan variable di url seperti </i>http://request.com/{id_pelanggan}}</i>.
* header: json array data header. Anda bisa menyelipkan variable di header.
<pre><code>
       "header": {
         "Content-Type":"application/json",
         "Authorization": "Bearer {{authorizationToken}}",
         "cache-control":"no-cache"
       }
</code></pre>
* data: data berupa json
* expected_response_type (optional): Jika ada hasil dari request yang ingin anda ambil, maka setel tipe data di sini. Saat ini tipe data yang didukung:
** int
** json
* extract (optional): Jika ada hasil dari request yang ingin anda ambil, maka anda harus mengatur konfigurasi ini.
** mapped-variable : nama variable tempat anda menyimpan data yang anda ekstrak dari request ini.
** type : tipe variable yang anda simpan
** datapath : jika data berupa json maka field apa yang harus anda ambil. 
Misalkan data anda adalah JSON seperti berikut:
<pre><code>
  {
    "giftcards": ["OHLALALA","AHLALALA"],
	"variable-lain": "apalah"
  }
</code></pre>
dan anda ingin mengambil data pertama dari field, maka datapath anda seperti ini:
<pre><code>
  "datapath":"giftCards[0]"
</code></pre>
* required (optional): jika anda ingin memastikan bahwa ada variable dari request ini yang bergantung pada variable yang diambil dari request sebelumnya. Nama variable berupa array.
contoh:
<pre><code>
  "required":["orderId"]
</code></pre>
* is_prerequisite (optional) : default <i>false</i>. Jika anda menandai <i>is_prerequisite</i> sebagai <i>true</i> maka waktu untuk request ini tidak akan dihitung. Penghitungan dimulai dari request setelahnya.


## Output
Hasil pengukuran oleh TembakWeb diletakkan di akhir. Jika TembakWeb dihentikan di tengah-tengah proses maka TembakWeb akan berusaha menghitung dari request yang sudah ditembakkan kecuali jika TembakWeb dihentikan dengan perintah <i>kill</i> (SIG_KILL).

Hasil outputnya akan memiliki format seperti ini:
<pre><code>
  INFO:root:Finished/interrupted after {{durasi waktu antara request pertama sampai response terakhir}}
  INFO:root:Start at {{waktu mulai}}
  INFO:root:End at {{ waktu selesai }}
  INFO:root:Number of Request    : {{jumlah request}}
  INFO:root:Number of concurrent at a time: {{jumlah request dalam batch (serentak)}}
  INFO:root:total duration (in s): {{ total durasi (kecuali pre-requisite request) }}
  INFO:root:min duration   (in s): {{ durasi minimal per transaksi (kecuali pre-requisite request)}}
  INFO:root:max duration   (in s): {{ durasi maksimal per transaksi (kecuali pre-requisite request)}}
  INFO:root:avg duration   (in s): {{ durasi rerata per transaksi (kecuali pre-requisite request}}
  INFO:root:num_of_ok_response    : {{jumlah request yang berhasil (request per transaksi x transaksi)}}
  INFO:root:num_of_error_response : {{ jumlah error }}
  INFO:root:num_of_incomplete_test: {{ jumlah transaksi tak selesai beserta persentase }}
  INFO:root:num_of_error          : {{ jumlah transaksi mengandung error beserta persentase }}
  INFO:root:num of status 200 : {{ jumlah request yang berstatus 200 }}
  INFO:root: ----- statistic per request --------- 

  {{kemudian looping tergantung banyaknya request per transaksi}}
  INFO:root: ----- statistic of request [{{index}}]--------- 
  INFO:root:url                  : {{ url dari request }}
  INFO:root:is_prerequisite      : {{ apakah request ini prerequisite? true/false }}
  INFO:root:total duration (in s): {{ total durasi untuk request jenis ini (tak peduli status code) }}
  INFO:root:min duration   (in s): {{ durasi terkecil untuk request jenis ini (tak peduli status code) }}
  INFO:root:max duration   (in s): {{ durasi terbesar untuk request jenis ini (tak peduli status code) }}
  INFO:root:avg duration   (in s): {{ durasi rerata untuk request jenis ini (tak peduli status code) }}
  INFO:root:total duration of ok request (in s): {{ total durasi untuk request jenis ini (hanya yang berhasil) }}
  INFO:root:min duration   of ok request (in s): {{ durasi terkecil untuk request jenis ini (hanya yang berhasil) }}
  INFO:root:max duration   of ok request (in s): {{ durasi terbesar untuk request jenis ini (hanya yang berhasil) }}
  INFO:root:avg duration   of ok request (in s): {{ durasi rerata untuk request jenis ini (hanya yang berhasil) }}
  
  {{kemudian jumlah status per jenis request, diurutkan berdasarkan jenis status kemudian jenis request}}
  INFO:root:num of status {{jenis status (200 atau error code)}} of request[{{index}}] : {{jumlah status beserta persentase}}
</code></pre>

# KolektorTokenOauth2 / TembakOauth2
Kolektor Token Oauth 2 adalah program terpisah, bertujuan untuk mengumpulkan token Oauth2 dari daftar user yang sudah disediakan.
User yang disediakan bisa ditaruh di dalam file .json dengan isi kurang lebih seperti ini:

for example:
<pre><code>
   { "users" = [{"username":"User Oneng", "password":"p4ssw0rd"},
                {"username":"User Twong", "password":"P566w0rd"}
               ]
   }
</code></pre>

Sama seperti TembakWeb, KolektorTokenAuth2 juga memiliki fitur untuk membungkus jika pengguna menginterupsi. 

Misalnya anda terlalu lama menunggu KolektorTokenAuth2 dan anda menekan <i>Ctrl+C</i> maka KolektorTokenAuth 2 akan membuat file .json dengan format seperti payload untuk loader.io berisi data token-token yang sudah dikumpulkan.

Konfigurasi KolektorTokenAuth2 ada di dalam file python yakni:
* filenamesource : nama file berisi daftar user
* fileoutput : nama file payload token yang akan dibuat
* filetemp : file sementara yang digunakan oleh KolektorTokenAuth2 untuk menyimpan hasil sebelum membuat payload. 
* num_of_concurrent_process : jumlah proses request secara paralel dalam satu waktu.
* client-id : client-id dari server Oauth2
* client-secret : client-secret dari server Oauth2
* oauth-url : url dari server Oauth2

Selain KolektorTokenAuth2, juga ada TembakOauth2 yang serupa dengan KolektorTokenOauth2 tetapi bisa serentak / paralel.

## Output KolektorTokenOauth2/TembakOauth2
Hasil dari tembakOauth2 berupa file yang sudah ditentukan di variable fileoutput dengan format berikut
<pre><code>
{
  "version": 1, 
  "variables": [
    {
      "names": ["token", "username"], 
      "values": [
        ["access_token_oauth2_nan_panjang_1", "username1"],
        ["access_token_oauth2_nan_panjang_2", "username2"],
        ["access_token_oauth2_nan_panjang_3", "username3"],
        ["access_token_oauth2_nan_panjang_dst", "usernamedst"]
        ]
    }]
}
</code></pre>

Hasil ini bisa digunakan sebagai payload untuk loader.io.




