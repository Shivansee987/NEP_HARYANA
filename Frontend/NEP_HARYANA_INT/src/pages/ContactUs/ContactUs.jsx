import React, { useState } from "react";
import { MapPin, Phone, Mail, Send, CheckCircle2 } from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import styles from "./ContactUs.module.css";

function ContactUs() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const recipient = "info@hshec.gov.in";
    const emailSubject = encodeURIComponent(formData.subject);
    const emailBody = encodeURIComponent(
      `Name: ${formData.name}\nFrom: ${formData.email}\n\n${formData.message}`
    );

    window.location.href = `mailto:${recipient}?subject=${emailSubject}&body=${emailBody}`;
  };

  return (
    <main className={styles.pageShell} id="main-content">
      <div className={styles.container}>
        
        {/* Logo and Header Block */}
        <section className={styles.headerBlock}>
          <div className={styles.logoFrame}>
            <img
              src={hshecLogo}
              alt="Haryana State Higher Education Council Logo"
              className={styles.logoImage}
            />
          </div>
          <div className={styles.accentLine} aria-hidden="true" />
          <h1 className={styles.pageTitle}>Contact HSHEC</h1>
          <p className={styles.pageSubtitle}>
            Get in touch with the Haryana State Higher Education Council. We are here to assist you with portal registration, evaluation queries, and technical support.
          </p>
        </section>

        {/* Contact Page Grid */}
        <section className={styles.contactGrid}>
          
          {/* Left Side: Contact Form */}
          <div className={styles.formCard}>
            <h2 className={styles.sectionHeading}>Send us a Message</h2>
            
            {submitted && (
              <div className={styles.successMessage}>
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>Thank you! Your message has been sent successfully. We will get back to you shortly.</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className={styles.contactForm}>
              <div className={styles.formGroup}>
                <label htmlFor="name">Your Name</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Enter your full name"
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="email">Official Email Address</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="name@institution.edu.in"
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="subject">Subject</label>
                <input
                  type="text"
                  id="subject"
                  name="subject"
                  value={formData.subject}
                  onChange={handleChange}
                  placeholder="Specify the topic"
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="message">Message</label>
                <textarea
                  id="message"
                  name="message"
                  rows="5"
                  value={formData.message}
                  onChange={handleChange}
                  placeholder="Write details of your query here..."
                  required
                />
              </div>

              <button type="submit" className={styles.submitBtn}>
                <Send className="w-4 h-4 shrink-0" />
                <span>Submit Inquiry</span>
              </button>
            </form>
          </div>

          {/* Right Side: Contact Details */}
          <div className={styles.detailsCard}>
            <h2 className={styles.sectionHeading}>Official Directory</h2>
            
            <div className={styles.contactList}>
              <div className={styles.contactItem}>
                <div className={styles.iconFrame}>
                  <MapPin className={styles.infoIcon} />
                </div>
                <div className={styles.infoContent}>
                  <h3>Office Address</h3>
                  <p>Plot No. 1A, Sector 5, Panchkula, Haryana — 134109</p>
                </div>
              </div>

              <div className={styles.contactItem}>
                <div className={styles.iconFrame}>
                  <Phone className={styles.infoIcon} />
                </div>
                <div className={styles.infoContent}>
                  <h3>Phone Number</h3>
                  <p>0172-2560888</p>
                  <p className={styles.subtext}>Available Mon-Fri, 9:00 AM - 5:00 PM</p>
                </div>
              </div>

              <div className={styles.contactItem}>
                <div className={styles.iconFrame}>
                  <Mail className={styles.infoIcon} />
                </div>
                <div className={styles.infoContent}>
                  <h3>Support Email</h3>
                  <p>info@hshec.gov.in</p>
                  <p className={styles.subtext}>For general and portal-related inquiries</p>
                </div>
              </div>
            </div>

            <div className={styles.mapAlert}>
              <h4>Technical Support Desk</h4>
              <p>For urgent accreditation issues, contact our DHE tech division directly at techsupport@hshec.gov.in.</p>
            </div>
          </div>

        </section>
      </div>
    </main>
  );
}

export default ContactUs;
