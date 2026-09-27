import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Phone, Mail } from 'lucide-react';
import hshecLogo from '../../assets/hshec_logo.jpeg';
import styles from './Footer.module.css';

/* ============================================
   SVG Icons
   ============================================ */

const IconFacebook = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
  </svg>
);

const IconTwitter = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5 2.8 12 3 12c.5.1 1 .1 1.5 0C2 10.5 2 6.5 2 6.5c.6.3 1.2.5 2 .5-1.3-1-2.4-3.5-1.5-5 2.5 3 6.5 5 10.5 5.5C12.5 2 18 2 20 6c1.2-.2 2.3-.7 3.3-1.3-.4 1.3-1.3 2.3-2.3 3z" />
  </svg>
);

const IconYouTube = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33 2.78 2.78 0 0 0 1.94 2c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.33 29 29 0 0 0-.46-5.33z" />
    <polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02" />
  </svg>
);

const IconLinkedIn = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

const ExternalLinkIcon = () => (
  <svg className={styles.externalIcon} width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
    <polyline points="15 3 21 3 21 9"></polyline>
    <line x1="10" y1="14" x2="21" y2="3"></line>
  </svg>
);

/* ============================================
   Component
   ============================================ */

function Footer() {
  return (
    <footer>
      {/* SECTION 1 — CTA Banner */}
      <div className={styles.ctaSection}>
        <div className={styles.ctaContainer}>
          <div className={styles.ctaText}>
            <h2 className={styles.ctaHeading}>Ready to submit your institutional data?</h2>
            <p className={styles.ctaSubtitle}>Register your college on the NEP 2020 evaluation portal today.</p>
          </div>
          <div className={styles.ctaButtons}>
            <Link to="/auth/login" className={styles.btnPrimary}>Get Started</Link>
            <Link to="/contact" className={styles.btnSecondary}>Contact Helpdesk</Link>
          </div>
        </div>
      </div>

      {/* SECTION 2 — Main Footer Body */}
      <div className={styles.footerMain}>
        <div className={styles.footerContainer}>
          
          {/* Column 1 — Brand & About */}
          <div className={styles.footerCol}>
            <div className={styles.brandHeader}>
              <div className={styles.logoCircle}>
                <img src={hshecLogo} alt="HSHEC Logo" className="w-full h-full object-contain" />
              </div>
              <div className={styles.brandText}>
                <span className={styles.brandTitle}>HSHEC</span>
                <span className={styles.brandSubtitle}>Govt. of Haryana</span>
              </div>
            </div>
            <p className={styles.brandDesc}>
              The apex statutory body for coordinated development of higher education in the State of Haryana.
            </p>
          </div>

          {/* Column 2 — Quick Links */}
          <div className={styles.footerCol}>
            <h3 className={styles.colHeading}>Quick Links</h3>
            <ul className={styles.linkList}>
              <li className={styles.linkItem}><a href="#" className={styles.footerLink}>About HSHEC</a></li>
              <li className={styles.linkItem}><a href="#" className={styles.footerLink}>Schemes & Awards</a></li>
              <li className={styles.linkItem}><a href="#" className={styles.footerLink}>Colleges Directory</a></li>
              <li className={styles.linkItem}><a href="#" className={styles.footerLink}>Notices & Tenders</a></li>
              <li className={styles.linkItem}><a href="#" className={styles.footerLink}>Contact Us</a></li>
            </ul>
          </div>

          {/* Column 3 — Important Links */}
          <div className={styles.footerCol}>
            <h3 className={styles.colHeading}>Important</h3>
            <ul className={styles.linkList}>
              <li className={styles.linkItem}>
                <a href="https://education.gov.in" target="_blank" rel="noopener noreferrer" className={styles.footerLink}>
                  Ministry of Education <ExternalLinkIcon />
                </a>
              </li>
              <li className={styles.linkItem}>
                <a href="https://ugc.ac.in" target="_blank" rel="noopener noreferrer" className={styles.footerLink}>
                  University Grants Commission <ExternalLinkIcon />
                </a>
              </li>
              <li className={styles.linkItem}>
                <a href="https://aishe.gov.in" target="_blank" rel="noopener noreferrer" className={styles.footerLink}>
                  AISHE Portal <ExternalLinkIcon />
                </a>
              </li>
              <li className={styles.linkItem}>
                <a href="https://india.gov.in" target="_blank" rel="noopener noreferrer" className={styles.footerLink}>
                  National Portal of India <ExternalLinkIcon />
                </a>
              </li>
              <li className={styles.linkItem}>
                <a href="https://haryana.gov.in" target="_blank" rel="noopener noreferrer" className={styles.footerLink}>
                  Haryana Government <ExternalLinkIcon />
                </a>
              </li>
            </ul>
          </div>

          {/* Column 4 — Reach Us */}
          <div className={styles.footerCol}>
            <h3 className={styles.colHeading}>Reach Us</h3>
            <ul className={styles.contactList}>
              <li className={styles.contactItem}>
                <MapPin className={`${styles.contactIcon} w-4 h-4 shrink-0`} />
                <span>Plot No. 1A, Sector 5, Panchkula, Haryana — 134109</span>
              </li>
              <li className={styles.contactItem}>
                <Phone className={`${styles.contactIcon} w-4 h-4 shrink-0`} />
                <span>0172-2560888</span>
              </li>
              <li className={styles.contactItem}>
                <Mail className={`${styles.contactIcon} w-4 h-4 shrink-0`} />
                <span>info@hshec.gov.in</span>
              </li>
            </ul>
            
            <div className={styles.socialRow}>
              <a href="#" className={styles.socialLink} aria-label="Facebook">
                <IconFacebook />
              </a>
              <a href="#" className={styles.socialLink} aria-label="Twitter">
                <IconTwitter />
              </a>
              <a href="#" className={styles.socialLink} aria-label="YouTube">
                <IconYouTube />
              </a>
              <a href="#" className={styles.socialLink} aria-label="LinkedIn">
                <IconLinkedIn />
              </a>
            </div>
          </div>

        </div>
      </div>

      {/* SECTION 3 — Footer Bottom Bar */}
      <div className={styles.footerBottom}>
        <div className={styles.bottomContainer}>
          <p className={styles.bottomText}>© 2026 Haryana State Higher Education Council. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
