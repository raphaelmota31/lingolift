# 🌍 LingoLift – Global PDF Translator

**LingoLift** is a desktop application that lets you translate the content of PDF files into multiple languages with ease. Built with `tkinter`, `PyPDF2`, and `googletrans`, it provides a simple interface and powerful backend for translating documents, preserving formatting, and even supporting fallback methods and resume functionality.

---

## 🚀 Features

- 📂 **Translate any PDF** into major global languages.
- 🌐 **Multilingual support** including Spanish, French, German, Chinese, Arabic, Japanese, and more.
- ⏸️ **Resume translation** from previous progress.
- 🛠️ **Fallback translator** option for large or complex documents.
- 📊 **Progress tracking** and responsive GUI.
- 📝 **Smart text wrapping** for multilingual formatting in the output PDF.

---

## 🖼️ UI Previews

Your `assets/` folder includes:

| File | Description |
|------|-------------|
| `ui` | Main application interface |
| `target_language` | Language selection dropdown |
| `progress` | Progress bar view |
| `success` | Success confirmation |

![UI Preview](./assets/ui)

---

## 🧰 Dependencies

Install these via `pip`:

```bash
pip install PyPDF2 googletrans==4.0.0-rc1 reportlab pdfplumber
```

Optional:

```bash
pip install translate ttkthemes tendo
```

---

## 📦 How to Run

```bash
python lingolift.py
```

On launch, select your input and output PDF, choose the target language, and hit **Translate PDF**. The app handles the rest — with a smooth interface and robust background threading.

---

## 🌍 Supported Languages

- English (`en`)
- Spanish (`es`)
- French (`fr`)
- German (`de`)
- Italian (`it`)
- Portuguese (`pt`)
- Russian (`ru`)
- Chinese Simplified (`zh-cn`)
- Japanese (`ja`)
- Arabic (`ar`)
- Hindi (`hi`)

---

## 📁 Progress & Resume

LingoLift saves progress in a JSON file during long translations. If interrupted, you can resume from where it left off by enabling the **Resume Previous Translation** option.

---

## 💡 Tips

- For large PDFs, enable **Fallback Translator** for better stability.
- Use system fonts like Arial or Mangal for enhanced language rendering.

---

## 📜 License

MIT License
