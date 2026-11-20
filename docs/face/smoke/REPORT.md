# Ket qua nhan dien khuon mat

> **SYNTHETIC SMOKE TEST.** Anh dau vao la hoa tiet ve, khong phai mat nguoi. Khong dua so nay vao bao cao mon hoc.

Day la bai chay thu tren anh hoa tiet ve bang code, khong phai khuon mat. Khong duoc chep cac so nay vao bao cao nhu do chinh xac cua he thong. SFace hoc tu mat nguoi that nen tren hoa tiet no thuong kem LBPH; dieu do khong noi LBPH tot hon khi co anh that. So sanh tai nguong da chon: lbph FAR=0 FRR=0.9375 misid=0 closed_acc=1 match_ms=1.78; sface FAR=0 FRR=1 misid=0 closed_acc=1 match_ms=0.04 feature_ms=7.66. closed_acc la accuracy tap kin: bat buoc gan dung nguoi gan nhat, khong co quyen tu choi. FAR/FRR/misid moi la so quyet dinh mo cua. match_ms la buoc so khop (LBPH predict hoac cosine tren vector co san). feature_ms la SFace ONNX. YuNet do rieng va cong them vao moi khung. Chon lbph vi cua nha uu tien khong mo nham. Thu tu: FAR thap nhat, roi nhan nham nguoi trong nha, roi FRR, roi accuracy tap kin, roi toc do CPU. Nguong 17.6418 (lbph), quy tac min_far_then_misid_then_frr. Nguon FAR: thu muc unknown/. FRR cao nghia la chu nha bi tu choi va phai bam nut Mo khoa bang tay. FAR cao nghia la nguoi la mo duoc cua. Nut tay luon con, ke ca khi model tu choi. FAR bang 0 di cung FRR cao nghia la nguong an toan dang nam o cho anh nguoi nha va anh nguoi la chong diem. FAR leave-one-person-out bang 0 trong truong hop do chu yeu vi nguong tu choi gan het anh, khong phai vi model tach nguoi la rat tot.

- Thoi diem: 2026-11-20T06:27:31Z
- May: Linux-6.12.113+-x86_64-with-glibc2.39, Python 3.12.3, OpenCV 4.10.0
- Thiet bi suy luan: CPU (khong bat CUDA)
- Seed chia tap: 42, ty le test: 0.3
- Nguoi hoc: mau_a, mau_b, mau_c, mau_d
- Anh train / test / nguoi la: 32 / 16 / 10
- Model chon cho bai nay: **lbph**
- Ghi model de chay cua: khong

## Tung mo hinh

### lbph

- Nguong: 17.6418 (lbph)
- Accuracy tap kin: 1
- FAR: 0, FRR: 0.9375, nhan nham trong nha: 0
- Do tre khop median / p95: 1.78 / 1.9 ms. LBPH predict tren anh xam 100x100, CPU, khong tinh thoi gian YuNet
- FAR leave-one-person-out (trung binh): 0
- Uoc luong FAR khi mot thanh vien chua dang ky. LBPH hoc lai moi lan nen thang diem co the lech model day du.

### sface

- Nguong: 0.9976 (cosine)
- Accuracy tap kin: 1
- FAR: 0, FRR: 1, nhan nham trong nha: 0
- Do tre khop median / p95: 0.04 / 0.04 ms. SFace cosine voi bo mau, CPU, vector da tinh san; thoi gian feature() tinh rieng
- Do tre feature median / p95: 7.66 / 8.52 ms. SFace feature() tren anh 112x112, CPU
- FAR leave-one-person-out (trung binh): 0
- Cung khong gian cosine voi model day du, nen nguong chuyen duoc sang bo mau co du nguoi.

## Gioi han

- Chua co chong gia mao: anh chup hoac man hinh dien thoai cua thanh vien van co the vuot nguong.
- Tap nho, cung mot webcam, anh sang phong demo. So se doi khi chup lai.
- YuNet cong them khoang 7.41 ms/khung tren CPU (do tren khung 640x480 trong).
