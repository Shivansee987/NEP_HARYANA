import { useState } from 'react';
import styles from './StudentStats.module.css';
import { validateUploadFile } from '../../utils/fileValidators';

const StudentStats = () => {
  const [formData, setFormData] = useState({
    totalStudents: '',
    maleStudents: '',
    femaleStudents: '',
    scStudents: '',
    stStudents: '',
    obcStudents: '',
    generalStudents: '',
    otherStateStudents: ''
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
          <h2>Student Statistics</h2>
          <p>Enter the demographic and enrollment statistics of students.</p>
        </div>
        
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label htmlFor="totalStudents">Total Students *</label>
              <input type="number" id="totalStudents" name="totalStudents" value={formData.totalStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="maleStudents">Total Male Students *</label>
              <input type="number" id="maleStudents" name="maleStudents" value={formData.maleStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="femaleStudents">Total Female Students *</label>
              <input type="number" id="femaleStudents" name="femaleStudents" value={formData.femaleStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="scStudents">SC Category Students *</label>
              <input type="number" id="scStudents" name="scStudents" value={formData.scStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="stStudents">ST Category Students *</label>
              <input type="number" id="stStudents" name="stStudents" value={formData.stStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="obcStudents">OBC Category Students *</label>
              <input type="number" id="obcStudents" name="obcStudents" value={formData.obcStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="generalStudents">General Category Students *</label>
              <input type="number" id="generalStudents" name="generalStudents" value={formData.generalStudents} onChange={handleChange} required />
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="otherStateStudents">Students from Other States</label>
              <input type="number" id="otherStateStudents" name="otherStateStudents" value={formData.otherStateStudents} onChange={handleChange} />
            </div>
          </div>

          <div className={styles.fileUploadSection}>
            <label>Supporting Document (Student Enrollment Register/Summary)</label>
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

export default StudentStats;
