import React, { useState } from 'react';
import styles from './AcademicInfo.module.css';
import { validateUploadFile } from '../../utils/fileValidators';

const AcademicInfo = () => {
  const [formData, setFormData] = useState({
    ugPrograms: '',
    pgPrograms: '',
    phdPrograms: '',
    totalStudents: '',
    passPercentage: '',
    dropoutRate: '',
    naacGrade: 'A++',
    lastNirfRank: ''
  });
  const [fileError, setFileError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileChange = async (e) => {
    setFileError('');
    const file = e.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      return;
    }
    const err = await validateUploadFile(file, { allowedFormats: ['pdf', 'png', 'jpg', 'jpeg'], isPdfOnly: false });
    if (err) {
      setFileError(err);
      setSelectedFile(null);
      e.target.value = '';
      return;
    }
    setSelectedFile(file);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (fileError) return;
    console.log('Form Submitted:', formData, selectedFile);
  };

  return (
    <div className={styles.pageContainer}>
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <h2>Academic Information</h2>
          <p>Enter the academic metrics and program details.</p>
        </div>
        
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label htmlFor="ugPrograms">Number of UG Programs *</label>
              <input type="number" id="ugPrograms" name="ugPrograms" value={formData.ugPrograms} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="pgPrograms">Number of PG Programs *</label>
              <input type="number" id="pgPrograms" name="pgPrograms" value={formData.pgPrograms} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="phdPrograms">Number of Ph.D. Programs</label>
              <input type="number" id="phdPrograms" name="phdPrograms" value={formData.phdPrograms} onChange={handleChange} />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="totalStudents">Total Students Enrolled *</label>
              <input type="number" id="totalStudents" name="totalStudents" value={formData.totalStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="passPercentage">Overall Pass Percentage (%) *</label>
              <input type="number" step="0.01" id="passPercentage" name="passPercentage" value={formData.passPercentage} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="dropoutRate">Drop-out Rate (%) *</label>
              <input type="number" step="0.01" id="dropoutRate" name="dropoutRate" value={formData.dropoutRate} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="naacGrade">NAAC Grade *</label>
              <select id="naacGrade" name="naacGrade" value={formData.naacGrade} onChange={handleChange} required>
                <option value="A++">A++</option>
                <option value="A+">A+</option>
                <option value="A">A</option>
                <option value="B++">B++</option>
                <option value="B+">B+</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="Not Accredited">Not Accredited</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="lastNirfRank">Last NIRF Rank (if any)</label>
              <input type="number" id="lastNirfRank" name="lastNirfRank" value={formData.lastNirfRank} onChange={handleChange} />
            </div>
          </div>

          <div className={styles.fileUploadSection}>
            <label>Supporting Document (NAAC Certificate / Academic Reports)</label>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className={styles.fileInput}
            />
            <p className={styles.fileHelp}>Upload PDF or Image (PDF strictly max 5 MB)</p>
            {fileError && (
              <p style={{ color: '#dc2626', fontSize: '0.8125rem', marginTop: '4px', fontWeight: 600 }}>
                {fileError}
              </p>
            )}
          </div>

          <div className={styles.actions}>
            <button type="submit" className={styles.submitBtn}>Save & Continue</button>
            <button type="button" className={styles.cancelBtn}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AcademicInfo;
