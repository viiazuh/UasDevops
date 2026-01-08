from flask import Flask, render_template, request, jsonify, send_from_directory
from catboost import CatBoostClassifier
import joblib
import numpy as np
import os
import sqlite3
from datetime import datetime
import pandas as pd
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", category=FutureWarning)

app = Flask(__name__)

# Load semua model
models = {}
try:
    models['catboost'] = CatBoostClassifier()
    models['catboost'].load_model('models/model_catboost.cbm')
    print("✅ Model CatBoost dimuat")
except Exception as e:
    print(f"❌ Error model CatBoost: {e}")

try:
    models['knn'] = joblib.load('models/model_knn.joblib')
    print("✅ Model KNN dimuat")
except Exception as e:
    print(f"❌ Error model KNN: {e}")

try:
    models['gb'] = joblib.load('models/model_gb.joblib')
    print("✅ Model Gradient Boosting dimuat")
except Exception as e:
    print(f"❌ Error model GB: {e}")

model = None
model_name = "Tidak Ada"

if 'gb' in models:
    model = models['gb']
    model_name = "Gradient Boosting"
    print("✅ Menggunakan Gradient Boosting ")
elif 'catboost' in models:
    model = models['catboost']
    model_name = "CatBoost"
    print("✅ Menggunakan CatBoost")
elif 'knn' in models:
    model = models['knn']
    model_name = "KNN"
    print("⚠️  Menggunakan KNN ")

print(f"🎯 Menggunakan model: {model_name}")

# Initialize database
def init_db():
    try:
        os.makedirs('database', exist_ok=True)
        conn = sqlite3.connect('database/prediksi_diabetes.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS prediksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usia INTEGER,
                jenis_kelamin TEXT,
                poliuria TEXT,
                polidipsia TEXT,
                penurunan_berat_badan TEXT,
                kelemahan TEXT,
                polifagia TEXT,
                infeksi_jamur TEXT,
                penglihatan_kabur TEXT,
                gatal_gatal TEXT,
                mudah_marah TEXT,
                penyembuhan_lambat TEXT,
                kelemahan_parsial TEXT,
                kekakuan_otot TEXT,
                kerontokan_rambut TEXT,
                obesitas TEXT,
                hasil_prediksi INTEGER,
                probabilitas REAL,
                model_digunakan TEXT,
                waktu_prediksi DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')    
        conn.commit()
        conn.close()
        print("✅ Database diinisialisasi dengan sukses")
    except Exception as e:
        print(f"❌ Error database: {e}")

init_db()

# ✅ ROUTE STATIC FILES
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# ✅ ROUTE BACKEND SEDERHANA
@app.route('/backend')
def backend_info():
    return """
    ============================================
    🚀 BACKEND DIABETES PREDICTION API
    ============================================
    
    📍 **API ENDPOINTS:**
    GET  /              → Frontend form (Diabetes prediction UI)
    GET  /backend       → This backend documentation
    POST /prediksi      → Predict diabetes (JSON API)
    GET  /riwayat       → Prediction history
    GET  /statistik     → Statistics
    DELETE /hapus/<id>  → Delete prediction
    
    🔧 **TECH STACK:**
    • Python Flask
    • Scikit-learn + CatBoost
    • SQLite Database
    • Docker Container
    • Kubernetes Deployment
    • Horizontal Pod Autoscaler (HPA)
    • CI/CD Pipeline
    
    🚀 **DEPLOYMENT INFO:**
    • Port 3000: Backend API Documentation
    • Port 5000: Frontend Application
    • Kubernetes: 2 replicas + HPA
    • Minikube Cluster
    
    📊 **MODEL INFO:**
    • Active Model: Gradient Boosting
    • Features: 16 clinical symptoms
    • Database: SQLite with prediction history
    
    ============================================
    UAS DEVOPS - CONTAINERIZED APPLICATION
    ============================================
    """

# ✅ ROUTE FRONTEND
@app.route('/')
def home():
    return render_template('prediction.html')

def apply_threshold_adjustment(raw_prediction, raw_probability, features, model_name):
    """
    Adjust prediction threshold untuk hasil yang lebih konservatif
    - Minimal 70% probability untuk prediksi diabetes
    - Minimal 2 gejala utama atau 3+ gejala total
    - Pertimbangan usia
    """
    # Hitung gejala utama (yang paling penting secara medis)
    main_symptoms = features[2:4]  # Hanya Polyuria dan Polydipsia - gejala paling khas diabetes
    secondary_symptoms = features[4:9]  # Gejala sekunder
    other_symptoms = features[9:14]  # Gejala lainnya
    
    main_symptom_count = sum(main_symptoms)
    secondary_symptom_count = sum(secondary_symptoms)
    other_symptom_count = sum(other_symptoms)
    total_symptoms = sum(features[2:14])  # Semua gejala kecuali age, gender, alopecia, obesity
    
    age = features[0]
    
    print(f"🔍 Threshold Check: main={main_symptom_count}, secondary={secondary_symptom_count}, other={other_symptom_count}, total={total_symptoms}, age={age}, raw_prob={raw_probability:.2f}")
    
    # ✅ KRITERIA KETAT UNTUK PREDIKSI DIABETES:
    if raw_prediction == 1:
        # 1. Probability harus > 65% (dinaikkan dari 50%)
        if raw_probability < 0.65:
            print(f"🔄 Adjust: Probability {raw_probability:.2f} < 65%, set to Normal")
            return 0, raw_probability
        
        # 2. Harus punya minimal 2 gejala utama ATAU 1 gejala utama + 2 sekunder ATAU 4+ gejala total
        if main_symptom_count < 2 and (main_symptom_count + secondary_symptom_count) < 3 and total_symptoms < 4:
            print(f"🔄 Adjust: Gejala tidak cukup (main={main_symptom_count}, total={total_symptoms}), set to Normal")
            return 0, raw_probability
        
        # 3. Jika usia muda (<30) butuh lebih banyak gejala
        if age < 30 and total_symptoms < 4:
            print(f"🔄 Adjust: Usia muda ({age}) dengan sedikit gejala ({total_symptoms}), set to Normal")
            return 0, raw_probability
            
        # 4. Jika hanya 1-2 gejala total, terlalu sedikit
        if total_symptoms <= 2:
            print(f"🔄 Adjust: Hanya {total_symptoms} gejala total, set to Normal")
            return 0, raw_probability
            
        # 5. Jika hanya gejala minor tanpa gejala utama, turunkan
        if main_symptom_count == 0 and total_symptoms < 5:
            print(f"🔄 Adjust: Tidak ada gejala utama dan hanya {total_symptoms} gejala, set to Normal")
            return 0, raw_probability
    
    # ✅ JIKA NORMAL TAPI PROBABILITY TINGGI + GEJALA KUAT, CEK LAGI
    elif raw_prediction == 0 and raw_probability > 0.60:
        # Jika punya 2+ gejala utama, mungkin ada risiko
        if main_symptom_count >= 2:
            print(f"🔄 Adjust: {main_symptom_count} gejala utama dengan prob {raw_probability:.2f}, set to Risk")
            return 1, raw_probability
            
        # Jika usia >45 dengan beberapa gejala
        if age > 45 and total_symptoms >= 3:
            print(f"🔄 Adjust: Usia {age} dengan {total_symptoms} gejala dan prob {raw_probability:.2f}, set to Risk")
            return 1, raw_probability
    
    print(f"✅ Final: prediction={raw_prediction}, probability={raw_probability:.2f}")
    return raw_prediction, raw_probability

def prediksi_fallback(features):
    """Improved fallback logic dengan threshold lebih tinggi"""
    # Gejala utama diabetes
    main_symptoms = features[2:4] 
    secondary_symptoms = features[4:9] 
    other_symptoms = features[9:14]
    
    main_symptom_count = sum(main_symptoms)
    secondary_symptom_count = sum(secondary_symptoms)
    other_symptom_count = sum(other_symptoms)
    total_symptoms = sum(features[2:14])
    age = features[0]
    
    print(f"🔍 Fallback Check: main={main_symptom_count}, secondary={secondary_symptom_count}, other={other_symptom_count}, total={total_symptoms}, age={age}")
    
    # ✅ KRITERIA KETAT UNTUK FALLBACK:
    # 1. Dua gejala utama langsung = risiko tinggi
    if main_symptom_count >= 2:
        probability = min(0.85, 0.70 + (total_symptoms * 0.05))
        return 1, probability
        
    # 2. Satu gejala utama + minimal 2 gejala lain
    elif main_symptom_count >= 1 and total_symptoms >= 3:
        probability = min(0.80, 0.65 + (total_symptoms * 0.04))
        return 1, probability
        
    # 3. Usia >45 dengan beberapa gejala
    elif age > 45 and total_symptoms >= 4:
        return 1, 0.70
        
    # 4. Banyak gejala sekunder (5+)
    elif total_symptoms >= 5:
        return 1, 0.65
        
    # 5. Normal cases
    else:
        base_prob = 0.20 + (total_symptoms * 0.03)
        return 0, min(0.45, base_prob)

@app.route('/prediksi', methods=['POST'])
def prediksi():
    conn = None
    try:
        data = request.json
        print(f"📥 Data received: {data}")

        # Preprocess data untuk model - 16 features lengkap
        features = [
            int(data.get('age', 0)),                   
            1 if data.get('gender') == 'Pria' else 0,   
            1 if data.get('polyuria') == 'Ya' else 0,  
            1 if data.get('polydipsia') == 'Ya' else 0, 
            1 if data.get('weight_loss') == 'Ya' else 0,
            1 if data.get('weakness') == 'Ya' else 0,   
            1 if data.get('polyphagia') == 'Ya' else 0, 
            1 if data.get('genital_thrush') == 'Ya' else 0, 
            1 if data.get('visual_blurring') == 'Ya' else 0, 
            1 if data.get('itching') == 'Ya' else 0,    
            1 if data.get('irritability') == 'Ya' else 0, 
            1 if data.get('delayed_healing') == 'Ya' else 0, 
            1 if data.get('partial_paresis') == 'Ya' else 0, 
            1 if data.get('muscle_stiffness') == 'Ya' else 0, 
            1 if data.get('alopecia') == 'Ya' else 0,   
            1 if data.get('obesity') == 'Ya' else 0    
        ]

        print(f"🔧 Features processed: {features}")
        
        current_model_name = model_name
        raw_prediction = 0
        raw_probability = 0.0
        
        if model and current_model_name != "Tidak Ada":
            try:
                if current_model_name == "CatBoost":
                    feature_names = [
                        'Age', 'Gender_Male', 'Polyuria_Yes', 'Polydipsia_Yes', 
                        'sudden weight loss_Yes', 'weakness_Yes', 'Polyphagia_Yes', 
                        'Genital thrush_Yes', 'visual blurring_Yes', 'Itching_Yes', 
                        'Irritability_Yes', 'delayed healing_Yes', 'partial paresis_Yes', 
                        'muscle stiffness_Yes', 'Alopecia_Yes', 'Obesity_Yes'
                    ]
                    
                    features_dict = {name: [value] for name, value in zip(feature_names, features)}
                    features_df = pd.DataFrame(features_dict)
                    
                    raw_prediction = model.predict(features_df)[0]
                    raw_probability = model.predict_proba(features_df)[0][1]
                    
                else:
                    raw_prediction = model.predict([features])[0]
                    raw_probability = model.predict_proba([features])[0][1]
                
                print(f"🤖 {current_model_name} raw prediction: {raw_prediction}, prob: {raw_probability:.2f}")
                
                # ✅ THRESHOLD ADJUSTMENT - Lebih konservatif
                prediction, probability = apply_threshold_adjustment(
                    raw_prediction, raw_probability, features, current_model_name
                )
                
                print(f"🎯 Final prediction: {prediction}, prob: {probability:.2f}")
                    
            except Exception as model_error:
                print(f"❌ Model prediction failed: {model_error}")
                prediction, probability = prediksi_fallback(features)
                current_model_name = f"Fallback ({current_model_name} failed)"
        else:
            prediction, probability = prediksi_fallback(features)
            current_model_name = "Logika Fallback"

        # Save to database dengan error handling - TANPA NAMA
        try:
            conn = sqlite3.connect('database/prediksi_diabetes.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO prediksi (
                    usia, jenis_kelamin, poliuria, polidipsia, 
                    penurunan_berat_badan, kelemahan, polifagia, infeksi_jamur, 
                    penglihatan_kabur, gatal_gatal, mudah_marah, penyembuhan_lambat, 
                    kelemahan_parsial, kekakuan_otot, kerontokan_rambut, obesitas,
                    hasil_prediksi, probabilitas, model_digunakan
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('age'), data.get('gender'),
                data.get('polyuria'), data.get('polydipsia'), data.get('weight_loss'),
                data.get('weakness'), data.get('polyphagia'), data.get('genital_thrush'),
                data.get('visual_blurring'), data.get('itching'), data.get('irritability'),
                data.get('delayed_healing'), data.get('partial_paresis'), data.get('muscle_stiffness'),
                data.get('alopecia'), data.get('obesity'),
                int(prediction), float(probability), current_model_name
            ))
            conn.commit()
            print("💾 Data berhasil disimpan ke database")
            
        except sqlite3.Error as db_error:
            print(f"❌ Database error: {db_error}")
        finally:
            if conn:
                conn.close()

        return jsonify({
            'success': True,
            'prediction': int(prediction),
            'probability': float(probability),
            'model_used': current_model_name,
            'diagnosis': 'Berisiko Diabetes' if prediction == 1 else 'Normal'
        })
        
    except Exception as e:
        print(f"❌ Error prediksi: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict_backup():
    print("⚠️  Menggunakan backup route /predict")
    return prediksi()

@app.route('/riwayat')
def riwayat():
    try:
        conn = sqlite3.connect('database/prediksi_diabetes.db')
        c = conn.cursor()
        c.execute('''
            SELECT id, usia, jenis_kelamin, hasil_prediksi, probabilitas, model_digunakan, waktu_prediksi
            FROM prediksi 
            ORDER BY waktu_prediksi DESC 
            LIMIT 50
        ''')
        records = c.fetchall()
        conn.close()
        
        riwayat_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Riwayat Prediksi Diabetes</title>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <h1>📊 Riwayat Prediksi Diabetes</h1>
                <a href="/" class="home-btn">← Kembali ke Prediksi</a>
                <br><br>
        '''
        
        if records:
            riwayat_html += '''
            <table>
                <tr>
                    <th>ID</th><th>Usia</th><th>Jenis Kelamin</th><th>Hasil</th>
                    <th>Probabilitas</th><th>Model</th><th>Waktu Prediksi</th><th>Aksi</th>
                </tr>
            '''
            for record in records:
                id, usia, gender, prediction, prob, model_used, timestamp = record
                result_text = "Berisiko Diabetes" if prediction == 1 else "Normal"
                row_class = "risk" if prediction == 1 else "normal"
                
                riwayat_html += f'''
                <tr class="{row_class}">
                    <td>{id}</td>
                    <td>{usia}</td>
                    <td>{gender}</td>
                    <td><strong>{result_text}</strong></td>
                    <td>{prob*100:.1f}%</td>
                    <td>{model_used}</td>
                    <td>{timestamp}</td>
                    <td><button class="delete-btn" onclick="hapusPrediksi({id})">Hapus</button></td>
                </tr>
                '''
            riwayat_html += '</table>'
            
            riwayat_html += '''
            <script>
                async function hapusPrediksi(id) {
                    if (confirm('Yakin ingin menghapus data ini?')) {
                        try {
                            const response = await fetch(`/hapus/${id}`, {
                                method: 'DELETE'
                            });
                            const result = await response.json();
                            if (result.success) {
                                alert('Data berhasil dihapus');
                                location.reload();
                            } else {
                                alert('Error: ' + result.error);
                            }
                        } catch (error) {
                            alert('Error: ' + error.message);
                        }
                    }
                }
            </script>
            '''
        else:
            riwayat_html += '<p>Belum ada data prediksi.</p>'
        
        riwayat_html += '</div></body></html>'
        return riwayat_html
        
    except Exception as e:
        return f"Error: {e}"

@app.route('/hapus/<int:prediction_id>', methods=['DELETE'])
def hapus_prediksi(prediction_id):
    try:
        conn = sqlite3.connect('database/prediksi_diabetes.db')
        c = conn.cursor()
        c.execute('DELETE FROM prediksi WHERE id = ?', (prediction_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Data berhasil dihapus'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/statistik')
def statistik():
    try:
        conn = sqlite3.connect('database/prediksi_diabetes.db')
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM prediksi')
        total = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM prediksi WHERE hasil_prediksi = 1')
        positive = c.fetchone()[0]
        
        c.execute('SELECT model_digunakan, COUNT(*) FROM prediksi GROUP BY model_digunakan')
        model_stats = c.fetchall()
        
        conn.close()
        
        stats_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Statistik Prediksi Diabetes</title>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <div class="container">
                <h1>📈 Statistik Prediksi Diabetes</h1>
                <a href="/" class="home-btn">← Kembali ke Prediksi</a>
                <br><br>
                
                <div class="stat-card">
                    <h3>Total Prediksi: {total}</h3>
                    <p>Berisiko Diabetes: {positive}</p>
                    <p>Normal: {total - positive}</p>
                    <p>Rasio: {positive/total*100:.1f if total > 0 else 0}% berisiko diabetes</p>
                </div>
                
                <div class="stat-card">
                    <h3>Penggunaan Model:</h3>
        '''
        
        for model_name, count in model_stats:
            stats_html += f'<p>{model_name}: {count} prediksi</p>'
        
        stats_html += '</div></div></body></html>'
        return stats_html
        
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    print("🚀 Aplikasi Prediksi Diabetes Dimulai!")
    print("📡 Backend: http://localhost:5000/backend")
    print("🖥️  Frontend: http://localhost:5000/")
    print(f"🎯 Model aktif: {model_name}")
    print("📊 Riwayat: http://localhost:5000/riwayat")
    print("📈 Statistik: http://localhost:5000/statistik")
    
    app.run(debug=True, host='0.0.0.0', port=5000)