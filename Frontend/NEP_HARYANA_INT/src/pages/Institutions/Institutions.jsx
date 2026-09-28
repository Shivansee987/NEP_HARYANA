import React, { useState, useMemo, useEffect } from "react";
import { Search, Building, Bookmark } from "lucide-react";
import { fetchColleges } from "../../api/auth";
import styles from "./Institutions.module.css";

function Institutions() {
  const [colleges, setColleges] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchColleges()
      .then((data) => setColleges(Array.isArray(data) ? data : data?.results || []))
      .catch(() => setColleges([]));
  }, []);

  const filteredColleges = useMemo(() => {
    const term = searchTerm.toLowerCase();
    return colleges.filter(
      (college) =>
        college.name.toLowerCase().includes(term) ||
        (college.aishe_code || "").toLowerCase().includes(term)
    );
  }, [colleges, searchTerm]);

  return (
    <main className={styles.pageShell} id="main-content">
      {/* Header Area */}
      <section className={styles.heroSection}>
        <div className={styles.container}>
          <div className={styles.accentLine} aria-hidden="true" />
          <h1 className={styles.pageTitle}>Participating Institutions</h1>
          <p className={styles.pageSubtitle}>
            Browse colleges and universities across Haryana participating in the NEP Excellence Awards evaluation.
          </p>
        </div>
      </section>

      {/* Filter and Search Section */}
      <section className={styles.filterSection}>
        <div className={styles.container}>
          <div className={styles.filterBar}>
            
            {/* Search Input */}
            <div className={styles.searchWrapper}>
              <Search className={styles.searchIcon} />
              <input
                type="text"
                placeholder="Search by name or AISHE code..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className={styles.searchInput}
              />
            </div>

          </div>
        </div>
      </section>

      {/* Grid List Section */}
      <section className={styles.listSection}>
        <div className={styles.container}>
          <div className={styles.resultsCount}>
            Showing {filteredColleges.length} of {colleges.length} institutions
          </div>

          <div className={styles.institutionsGrid}>
            {filteredColleges.map((college) => (
              <div key={college.id} className={styles.collegeCard}>
                <div className={styles.cardHeader}>
                  <div className={styles.iconFrame}>
                    <Building className={styles.buildingIcon} />
                  </div>
                </div>

                <div className={styles.cardBody}>
                  <h2 className={styles.collegeName}>{college.name}</h2>
                  
                  <div className={styles.metaRow}>
                    <div className={styles.metaItem}>
                      <Bookmark className={styles.metaIcon} />
                      <span>AISHE: {college.aishe_code}</span>
                    </div>
                  </div>
                </div>

                <div className={styles.cardFooter}>
                  <div className={`${styles.statusLabel} ${styles.statusPending}`}>Registered</div>
                  <span className={styles.viewDetails}>NEP Awards 2026</span>
                </div>
              </div>
            ))}

            {filteredColleges.length === 0 && (
              <div className={styles.noResults}>
                <h3>No institutions found</h3>
                <p>Try refining your search terms.</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

export default Institutions;
