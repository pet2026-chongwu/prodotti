# 更新 PET World 公开目录

客户扫描原名片二维码，仍打开 `index_2.html`。

首次在电脑上安装 Python 3 和 Pillow（Windows 可运行 `py -m pip install Pillow`），并下载或克隆本仓库的最新版本。把系统导出的 CSV 和照片压缩包放到仓库外。双击 `Aggiorna-Catalogo.bat`，依次选择 CSV 和图片包。没有新图时，第二个窗口点取消。

也可以在仓库目录用 PowerShell 运行：

```powershell
py aggiorna_catalogo.py "C:\\路径\\product_2026-11-16.csv" "C:\\路径\\20261116.tar.gz"
```

没有新照片时，可以只传 CSV。脚本按型号复用已有照片，压缩包里的同名照片会替换原图。CSV 是完整目录快照，其中没有的型号会从公开目录移除。

用 GitHub Desktop 提交并推送 `catalogo/` 的改动，待 GitHub Pages 部署完成后打开原二维码链接核对。只上传生成的文件，原始 CSV 和压缩包应留在电脑。本脚本仅导出型号、意大利语名称、条码、分类、包装数量和商品图片。

老型号保留原分类，新型号按意大利语商品名自动分类。需要手动指定时，在 `catalogo/categorie.json` 中加入 `"商品型号": ["主分类", "子分类"]`，再运行脚本。

本地预览可运行 `py -m http.server 8000`，然后打开 `http://localhost:8000/index_2.html`。
