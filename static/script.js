// // Konfigurasi
// const PREDICTION_ENDPOINT = '/prediksi';

// // Elemen DOM
// let predictionForm, submitBtn, resultContainer;

// // Inisialisasi ketika DOM siap
// document.addEventListener('DOMContentLoaded', function() {
//     initializeApp();
// });

// function initializeApp() {
//     predictionForm = document.getElementById('predictionForm');
//     submitBtn = document.getElementById('submitBtn');
//     resultContainer = document.getElementById('resultContainer');
    
//     if (predictionForm) {
//         predictionForm.addEventListener('submit', handleFormSubmit);
//     }
// }

// async function handleFormSubmit(e) {
//     e.preventDefault();
    
//     const formData = new FormData(predictionForm);
//     const data = Object.fromEntries(formData);
    
//     const validationErrors = validateForm(data);
//     if (validationErrors.length > 0) {
//         alert("Mohon lengkapi semua field:\n" + validationErrors.join('\n'));
//         return;
//     }

//     setLoadingState(true);
//     resultContainer.innerHTML = '<div class="loading">🔄 Memproses prediksi...</div>';

//     try {
//         const response = await fetch(PREDICTION_ENDPOINT, {
//             method: "POST",
//             headers: { 
//                 "Content-Type": "application/json",
//                 "Accept": "application/json"
//             },
//             body: JSON.stringify(data),
//         });
        
//         if (!response.ok) {
//             throw new Error(`HTTP ${response.status}`);
//         }
        
//         const result = await response.json();

//         if (result.error) {
//             throw new Error(result.error);
//         }

//         displayPredictionResult(result);

//     } catch (error) {
//         console.error("❌ Terjadi kesalahan:", error);
//         displayError("Terjadi kesalahan saat memproses prediksi. Silakan coba lagi.");
//     } finally {
//         setLoadingState(false);
//     }
// }

// function setLoadingState(isLoading) {
//     if (submitBtn) {
//         submitBtn.disabled = isLoading;
//         submitBtn.textContent = isLoading ? 'Memproses...' : 'Prediksi Sekarang';
//     }
// }

// function displayPredictionResult(result) {
//     const diagnosis = result.diagnosis;
//     const resultClass = result.prediction === 1 ? "diabetic" : "normal";
//     const probability = (result.probability * 100).toFixed(1);
//     const advice = result.prediction === 1 ? 
//         '⚠️ Disarankan untuk konsultasi dengan dokter dan melakukan pemeriksaan gula darah. Gejala yang dialami menunjukkan kemungkinan diabetes.' : 
//         '✅ Hasil menunjukkan risiko diabetes rendah. Tetap jaga pola hidup sehat dengan diet seimbang dan olahraga teratur.';
    
//     const resultHTML = `
//         <div class="result ${resultClass}">
//             <h3>Hasil Prediksi:</h3>
//             <div class="diagnosis-badge">${diagnosis}</div>
//             <div class="confidence">Tingkat Kepercayaan: <strong>${probability}%</strong></div>
//             <div class="model-info">Model yang digunakan: <strong>${result.model_used}</strong></div>
//             <div class="advice">${advice}</div>
//             <div class="nav-links">
//                 <a href="/riwayat" class="nav-btn">📊 Lihat Riwayat</a>
//                 <a href="/statistik" class="nav-btn">📈 Lihat Statistik</a>
//                 <button onclick="location.reload()" class="nav-btn">🔄 Prediksi Lagi</button>
//             </div>
//         </div>
//     `;
    
//     resultContainer.innerHTML = resultHTML;
// }

// function displayError(errorMessage) {
//     const errorHTML = `
//         <div class="result error">
//             <h3>❌ Terjadi Kesalahan</h3>
//             <p>${errorMessage}</p>
//             <div class="nav-links">
//                 <button onclick="location.reload()" class="nav-btn">🔄 Refresh Halaman</button>
//                 <a href="/" class="nav-btn">🏠 Kembali ke Home</a>
//             </div>
//         </div>
//     `;
    
//     resultContainer.innerHTML = errorHTML;
// }

// function validateForm(data) {
//     const errors = [];
    
//     if (!data.name || data.name.trim().length < 2) {
//         errors.push('• Nama harus diisi (minimal 2 karakter)');
//     }
    
//     if (!data.age || data.age < 1 || data.age > 120) {
//         errors.push('• Usia harus antara 1-120 tahun');
//     }
    
//     if (!data.gender) {
//         errors.push('• Jenis kelamin harus dipilih');
//     }
    
//     const symptoms = [
//         'polyuria', 'polydipsia', 'weight_loss', 'weakness', 
//         'polyphagia', 'genital_thrush', 'visual_blurring', 
//         'itching', 'irritability', 'delayed_healing', 
//         'partial_paresis', 'muscle_stiffness',
//         'alopecia', 'obesity'
//     ];
    
//     symptoms.forEach(symptom => {
//         if (!data[symptom]) {
//             errors.push(`• Semua gejala harus dipilih`);
//             return;
//         }
//     });
    
//     return errors;
// }


