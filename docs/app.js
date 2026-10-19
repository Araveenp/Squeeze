/* ==========================================================================
   Squeeze — Product Landing Page JavaScript
   Interactive Radial HUD Simulator, ScrollSpy & UI Handlers
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initSimulator();
  initScrollSpy();
  initCopyButtons();
  initMobileNav();
});

// --------------------------------------------------------------------------
// 1. Theme Toggle (Dark / Light)
// --------------------------------------------------------------------------
function initThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;

  const savedTheme = localStorage.getItem('squeeze-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  toggleBtn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('squeeze-theme', next);
    updateThemeIcon(next);
  });
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (!icon) return;
  if (theme === 'dark') {
    icon.innerHTML = `<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>`;
  } else {
    icon.innerHTML = `<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path>`;
  }
}

// --------------------------------------------------------------------------
// 2. Interactive Squeeze Radial HUD Simulator
// --------------------------------------------------------------------------
function initSimulator() {
  const wedges = document.querySelectorAll('.wedge-interactive');
  const statSelected = document.getElementById('sim-stat-selected');
  const statOriginal = document.getElementById('sim-stat-original');
  const statOutput = document.getElementById('sim-stat-output');
  const statSaved = document.getElementById('sim-stat-saved');
  const statFileOut = document.getElementById('sim-file-out');
  const simProgressBar = document.getElementById('sim-progress-bar');

  // Wedge configuration data mirroring engine.py logic
  const wedgeData = {
    'q-low': {
      title: 'Quality: Low (q=40)',
      orig: '4.8 MB',
      output: '620 KB',
      saved: '87.1%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'Aggressive DCT quantization. Best for thumbnails and quick web previews.'
    },
    'q-med': {
      title: 'Quality: Medium (q=65)',
      orig: '4.8 MB',
      output: '1.1 MB',
      saved: '77.0%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'Default sweet spot. Imperceptible visual loss, massive file size reduction.'
    },
    'q-high': {
      title: 'Quality: High (q=85)',
      orig: '4.8 MB',
      output: '2.1 MB',
      saved: '56.2%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'Near-lossless visual fidelity. Retains fine grain and high-frequency details.'
    },
    's-100k': {
      title: 'Target Size: < 100 KB',
      orig: '4.8 MB',
      output: '98 KB',
      saved: '97.9%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'Fits strict upload forms. Scales down resolution only if quality floor is hit.'
    },
    's-500k': {
      title: 'Target Size: < 500 KB',
      orig: '4.8 MB',
      output: '480 KB',
      saved: '90.0%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'Ideal for email attachments and mobile chat sharing.'
    },
    's-1m': {
      title: 'Target Size: < 1 MB',
      orig: '4.8 MB',
      output: '960 KB',
      saved: '80.0%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'The standard modern web image threshold. Retains full resolution.'
    },
    's-2m': {
      title: 'Target Size: < 2 MB',
      orig: '4.8 MB',
      output: '1.9 MB',
      saved: '60.4%',
      file: 'vacation_photo_compressed.jpg',
      desc: 'Generous ceiling for 4K desktop wallpapers and high-res scans.'
    },
    'zip': {
      title: 'ZIP Archive Mode',
      orig: '4.8 MB',
      output: '3.4 MB',
      saved: '29.1%',
      file: 'Archive.zip',
      desc: 'Instantly packs selected files or directories into a clean standard ZIP container.'
    }
  };

  wedges.forEach(wedge => {
    wedge.addEventListener('mouseenter', () => {
      const id = wedge.getAttribute('data-wedge-id');
      selectWedge(id, wedge);
    });

    wedge.addEventListener('click', () => {
      const id = wedge.getAttribute('data-wedge-id');
      selectWedge(id, wedge);
      triggerPulseEffect();
    });
  });

  function selectWedge(id, activeEl) {
    const data = wedgeData[id];
    if (!data) return;

    // Remove active class from all wedges
    wedges.forEach(w => w.classList.remove('active'));
    activeEl.classList.add('active');

    // Update stats
    if (statSelected) statSelected.textContent = data.title;
    if (statOriginal) statOriginal.textContent = data.orig;
    if (statOutput) statOutput.textContent = data.output;
    if (statSaved) statSaved.textContent = `-${data.saved}`;
    if (statFileOut) statFileOut.textContent = data.file;

    // Animate progress bar
    if (simProgressBar) {
      simProgressBar.style.width = '0%';
      setTimeout(() => {
        const percentage = 100 - parseFloat(data.saved);
        simProgressBar.style.width = `${percentage}%`;
      }, 50);
    }
  }

  function triggerPulseEffect() {
    const center = document.querySelector('.hud-center');
    if (center) {
      center.style.transform = 'scale(0.92)';
      setTimeout(() => {
        center.style.transform = 'scale(1)';
      }, 150);
    }
  }

  // Pre-select default (Medium / 1 MB)
  const defaultWedge = document.querySelector('[data-wedge-id="q-med"]');
  if (defaultWedge) {
    selectWedge('q-med', defaultWedge);
  }
}

// --------------------------------------------------------------------------
// 3. ScrollSpy for Floating Right Navigation
// --------------------------------------------------------------------------
function initScrollSpy() {
  const sections = document.querySelectorAll('section[id]');
  const tocLinks = document.querySelectorAll('.floating-toc a');
  if (!sections.length || !tocLinks.length) return;

  window.addEventListener('scroll', () => {
    let currentId = '';
    const scrollPos = window.scrollY + 200;

    sections.forEach(section => {
      const top = section.offsetTop;
      const height = section.offsetHeight;
      if (scrollPos >= top && scrollPos < top + height) {
        currentId = section.getAttribute('id');
      }
    });

    tocLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === `#${currentId}`) {
        link.classList.add('active');
      }
    });
  });
}

// --------------------------------------------------------------------------
// 4. Clipboard Copy Utilities
// --------------------------------------------------------------------------
function initCopyButtons() {
  // Share link copy
  const shareCopyBtn = document.getElementById('share-copy-link');
  if (shareCopyBtn) {
    shareCopyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(window.location.href).then(() => {
        const label = shareCopyBtn.querySelector('.share-label');
        if (label) {
          const prev = label.textContent;
          label.textContent = 'Copied!';
          setTimeout(() => { label.textContent = prev; }, 2000);
        }
      });
    });
  }

  // Code snippet copy
  const copyCodeBtn = document.getElementById('copy-source-code');
  if (copyCodeBtn) {
    copyCodeBtn.addEventListener('click', () => {
      const code = `git clone https://github.com/Araveenp/Squeeze.git\ncd Squeeze\npy -m pip install -r requirements.txt\npythonw app.py`;
      navigator.clipboard.writeText(code).then(() => {
        copyCodeBtn.textContent = 'COPIED TO CLIPBOARD';
        setTimeout(() => {
          copyCodeBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg> COPY COMMANDS`;
        }, 2200);
      });
    });
  }
}

// --------------------------------------------------------------------------
// 5. Mobile Navigation (Hamburger Menu)
// --------------------------------------------------------------------------
function initMobileNav() {
  const hamburgerBtn = document.getElementById('nav-hamburger');
  const drawer = document.getElementById('mobile-nav-drawer');
  const hamburgerIcon = document.getElementById('hamburger-icon');
  if (!hamburgerBtn || !drawer) return;

  const openIcon = `<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>`;
  const closeIcon = `<line x1="4" y1="4" x2="20" y2="20"/><line x1="20" y1="4" x2="4" y2="20"/>`;

  function openDrawer() {
    drawer.classList.add('open');
    hamburgerBtn.setAttribute('aria-expanded', 'true');
    if (hamburgerIcon) hamburgerIcon.innerHTML = closeIcon;
  }

  function closeDrawer() {
    drawer.classList.remove('open');
    hamburgerBtn.setAttribute('aria-expanded', 'false');
    if (hamburgerIcon) hamburgerIcon.innerHTML = openIcon;
  }

  hamburgerBtn.addEventListener('click', () => {
    drawer.classList.contains('open') ? closeDrawer() : openDrawer();
  });

  // Close drawer when any link inside it is clicked
  drawer.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => closeDrawer());
  });

  // Close drawer on resize back to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeDrawer();
  });
}
