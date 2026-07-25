# QuickTools - Free Online Tools Website

Flask-la build panna free tools website. Word Counter, QR Generator, Unit Converter,
Temperature Converter, Image Compressor - ella tools um irukku.

## 🚀 PyCharm-la Run Panna Steps

1. **Project open pannunga**: PyCharm open panni indha `quicktools` folder-a open pannunga
   (File > Open > select the `quicktools` folder).

2. **Virtual environment create pannunga** (PyCharm automatic-ah kekum, "Yes" click pannunga):
   - Illa manual-ah terminal-la:
     ```
     python -m venv venv
     venv\Scripts\activate      # Windows
     source venv/bin/activate   # Mac/Linux
     ```

3. **Dependencies install pannunga** (PyCharm terminal-la):
   ```
   pip install -r requirements.txt
   ```

4. **Run pannunga**: `app.py` file open panni, top-right-la irukura green ▶️ Run button
   click pannunga. Illa terminal-la:
   ```
   python app.py
   ```

5. Browser-la open pannunga: **http://127.0.0.1:5000**

## 📂 Project Structure

```
quicktools/
├── app.py                  # Main Flask app - ella routes um inga
├── requirements.txt        # Python packages
├── templates/               # HTML pages
│   ├── base.html            # Common layout (navbar, footer, ad slots)
│   ├── index.html           # Home page
│   ├── word_counter.html
│   ├── qr_generator.html
│   ├── unit_converter.html
│   ├── temperature_converter.html
│   └── image_compressor.html
└── static/
    └── style.css             # Styling
```

## 💰 Revenue Setup (Ads/Affiliate) - Next Steps

1. **Domain vaangunga** (e.g., Namecheap, GoDaddy) - ~₹500-1000/year.
2. **Deploy pannunga** free/cheap hosting-la:
   - [Render.com](https://render.com) - free tier available, Flask apps easy-ah deploy pannalam
   - [Railway.app](https://railway.app)
   - [PythonAnywhere](https://www.pythonanywhere.com) - free tier
3. **Traffic vandhadhum**, [Google AdSense](https://www.google.com/adsense/) apply pannunga
   (approval ku minimum kaalam wait pannanum + good content venum).
   - AdSense approve aana pinnadi, `templates/base.html` file-la irukura ad script
     uncomment panni unga publisher ID podunga.
4. **More traffic-ku**: SEO friendly content (blog section add pannalam), social media
   share pannunga, Google Search Console-la site submit pannunga.

## ➕ Adding More Tools

Puthu tool add panna:
1. `app.py`-la puthu `@app.route()` function add pannunga.
2. `templates/` folder-la puthu `.html` file create pannunga (base.html extend pannunga).
3. `templates/base.html` navbar-la link add pannunga.

Ideas for more tools: PDF merger, Password generator, Text-to-speech,
Color picker, Age calculator, EMI calculator.

## ⚠️ Note

Idhu development server (`debug=True`). Production-ku deploy panna mun,
`app.run(debug=True)` ah `debug=False` ah maathunga, and Gunicorn/Waitress
maadhiri production server use pannunga.
