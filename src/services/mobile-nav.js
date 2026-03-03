/**
 * Mobile Navigation Module - Hamburger menu with slide-in drawer
 * 
 * Usage:
 *   import { initMobileNav, injectMobileNavStyles } from './services/mobile-nav.js';
 *   injectMobileNavStyles();
 *   initMobileNav();
 * 
 * Only activates on mobile (max-width: 768px)
 */

const MOBILE_BREAKPOINT = 768;

/**
 * CSS styles for mobile navigation
 */
const mobileNavStyles = `
/* ============================================
   MOBILE NAVIGATION - Only visible <= 768px
   ============================================ */

/* Hamburger button - hidden on desktop */
.mobile-hamburger {
    display: none;
    background: none;
    border: none;
    padding: 8px;
    cursor: pointer;
    z-index: 100;
}

.mobile-hamburger__icon {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 24px;
    height: 18px;
}

.mobile-hamburger__line {
    display: block;
    height: 2px;
    width: 100%;
    background-color: #333;
    border-radius: 2px;
    transition: transform 0.3s ease, opacity 0.3s ease;
}

/* Hamburger animation when open */
.mobile-hamburger.is-open .mobile-hamburger__line:nth-child(1) {
    transform: translateY(8px) rotate(45deg);
}

.mobile-hamburger.is-open .mobile-hamburger__line:nth-child(2) {
    opacity: 0;
}

.mobile-hamburger.is-open .mobile-hamburger__line:nth-child(3) {
    transform: translateY(-8px) rotate(-45deg);
}

/* Mobile menu overlay */
.mobile-menu-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 9998;
    opacity: 0;
    transition: opacity 0.25s ease;
    backdrop-filter: blur(2px);
}

.mobile-menu-overlay.is-visible {
    opacity: 1;
}

/* Slide-in drawer */
.mobile-drawer {
    display: none;
    position: fixed;
    top: 0;
    right: 0;
    width: 280px;
    max-width: 85vw;
    height: 100%;
    background: #fff;
    z-index: 9999;
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
    overflow-y: auto;
}

.mobile-drawer.is-open {
    transform: translateX(0);
}

.mobile-drawer__header {
    padding: 20px;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.mobile-drawer__title {
    font-size: 18px;
    font-weight: 600;
    color: #222;
}

.mobile-drawer__close {
    background: none;
    border: none;
    font-size: 24px;
    color: #666;
    cursor: pointer;
    padding: 4px 8px;
    line-height: 1;
}

.mobile-drawer__close:hover {
    color: #333;
}

.mobile-drawer__menu {
    list-style: none;
    margin: 0;
    padding: 0;
}

.mobile-drawer__item {
    border-bottom: 1px solid #f0f0f0;
}

.mobile-drawer__link {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    color: #333;
    text-decoration: none;
    font-size: 15px;
    font-weight: 500;
    transition: background-color 0.15s ease;
    cursor: pointer;
    background: none;
    border: none;
    width: 100%;
    text-align: left;
}

.mobile-drawer__link:hover,
.mobile-drawer__link:focus {
    background-color: #f8f8f8;
}

.mobile-drawer__link--danger {
    color: #d90429;
}

.mobile-drawer__link--danger:hover {
    background-color: #fff5f5;
}

.mobile-drawer__icon {
    font-size: 18px;
    width: 24px;
    text-align: center;
}

/* User info in drawer */
.mobile-drawer__user {
    padding: 16px 20px;
    background: #f8f8f8;
    border-bottom: 1px solid #eee;
}

.mobile-drawer__user-email {
    font-size: 13px;
    color: #666;
    word-break: break-all;
}

/* ============================================
   MOBILE MEDIA QUERY
   ============================================ */
@media (max-width: 768px) {
    /* Show hamburger on mobile */
    .mobile-hamburger {
        display: block;
    }

    /* Show overlay and drawer structure on mobile */
    .mobile-menu-overlay,
    .mobile-drawer {
        display: block;
    }

    /* Hide desktop menu items on mobile */
    .user-menu > button,
    .user-menu > .profile-btn,
    .user-menu > .logout-btn,
    .header-actions > button,
    .header-content > .header-btn {
        display: none !important;
    }

    /* Keep user email hidden on mobile too */
    .user-menu > span#userEmail {
        display: none !important;
    }

    /* Adjust header layout for mobile */
    .header-container,
    .header-content {
        justify-content: space-between;
    }

    /* Prevent body scroll when menu is open */
    body.mobile-menu-open {
        overflow: hidden;
    }
}
`;

let stylesInjected = false;
let isMenuOpen = false;

/**
 * Inject mobile navigation styles
 */
export function injectMobileNavStyles() {
    if (stylesInjected || typeof document === 'undefined') return;

    const styleEl = document.createElement('style');
    styleEl.id = 'mobile-nav-styles';
    styleEl.textContent = mobileNavStyles;
    document.head.appendChild(styleEl);
    stylesInjected = true;
}

/**
 * Create hamburger button HTML
 */
function createHamburgerButton() {
    const btn = document.createElement('button');
    btn.className = 'mobile-hamburger';
    btn.setAttribute('aria-label', 'Open menu');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = `
        <span class="mobile-hamburger__icon">
            <span class="mobile-hamburger__line"></span>
            <span class="mobile-hamburger__line"></span>
            <span class="mobile-hamburger__line"></span>
        </span>
    `;
    return btn;
}

/**
 * Create mobile drawer HTML
 */
function createMobileDrawer(userEmail) {
    const overlay = document.createElement('div');
    overlay.className = 'mobile-menu-overlay';
    overlay.id = 'mobileMenuOverlay';

    const drawer = document.createElement('div');
    drawer.className = 'mobile-drawer';
    drawer.id = 'mobileDrawer';
    drawer.innerHTML = `
        <div class="mobile-drawer__header">
            <span class="mobile-drawer__title">Menu</span>
            <button class="mobile-drawer__close" aria-label="Close menu">&times;</button>
        </div>
        ${userEmail ? `
        <div class="mobile-drawer__user">
            <div class="mobile-drawer__user-email">${userEmail}</div>
        </div>
        ` : ''}
        <ul class="mobile-drawer__menu">
            <li class="mobile-drawer__item">
                <a href="home.html" class="mobile-drawer__link">
                    <span class="mobile-drawer__icon">🏠</span>
                    Home
                </a>
            </li>
            <li class="mobile-drawer__item">
                <a href="profile.html" class="mobile-drawer__link">
                    <span class="mobile-drawer__icon">👤</span>
                    My Profile
                </a>
            </li>
            <li class="mobile-drawer__item">
                <button class="mobile-drawer__link" id="mobileDrawerBecomeHost">
                    <span class="mobile-drawer__icon">🏡</span>
                    Become a Host
                </button>
            </li>
            <li class="mobile-drawer__item">
                <button class="mobile-drawer__link mobile-drawer__link--danger" id="mobileDrawerLogout">
                    <span class="mobile-drawer__icon">🚪</span>
                    Logout
                </button>
            </li>
        </ul>
    `;

    return { overlay, drawer };
}

/**
 * Open mobile menu
 */
function openMenu(hamburger, overlay, drawer) {
    isMenuOpen = true;
    hamburger.classList.add('is-open');
    hamburger.setAttribute('aria-expanded', 'true');
    overlay.classList.add('is-visible');
    drawer.classList.add('is-open');
    document.body.classList.add('mobile-menu-open');
}

/**
 * Close mobile menu
 */
function closeMenu(hamburger, overlay, drawer) {
    isMenuOpen = false;
    hamburger.classList.remove('is-open');
    hamburger.setAttribute('aria-expanded', 'false');
    overlay.classList.remove('is-visible');
    drawer.classList.remove('is-open');
    document.body.classList.remove('mobile-menu-open');
}

/**
 * Initialize mobile navigation
 * Call this after DOM is ready
 */
export function initMobileNav() {
    if (typeof window === 'undefined') return;

    // Only initialize on mobile
    const isMobile = () => window.innerWidth <= MOBILE_BREAKPOINT;

    // Find header
    const header = document.querySelector('header .header-container') ||
                   document.querySelector('header .header-content');
    if (!header) return;

    // Get user email if available
    const userEmail = localStorage.getItem('userEmail') || '';

    // Create elements
    const hamburger = createHamburgerButton();
    const { overlay, drawer } = createMobileDrawer(userEmail);

    // Add hamburger to header
    header.appendChild(hamburger);

    // Add overlay and drawer to body
    document.body.appendChild(overlay);
    document.body.appendChild(drawer);

    // Get references
    const closeBtn = drawer.querySelector('.mobile-drawer__close');
    const becomeHostBtn = drawer.querySelector('#mobileDrawerBecomeHost');
    const logoutBtn = drawer.querySelector('#mobileDrawerLogout');

    // Event handlers
    hamburger.addEventListener('click', () => {
        if (isMenuOpen) {
            closeMenu(hamburger, overlay, drawer);
        } else {
            openMenu(hamburger, overlay, drawer);
        }
    });

    overlay.addEventListener('click', () => {
        closeMenu(hamburger, overlay, drawer);
    });

    closeBtn.addEventListener('click', () => {
        closeMenu(hamburger, overlay, drawer);
    });

    // Become a Host - trigger existing modal
    becomeHostBtn.addEventListener('click', () => {
        closeMenu(hamburger, overlay, drawer);
        const modal = document.getElementById('comingSoonModal');
        if (modal) {
            modal.classList.add('show');
        }
    });

    // Logout - trigger existing logout function or modal
    logoutBtn.addEventListener('click', () => {
        closeMenu(hamburger, overlay, drawer);
        // Try to call existing logout function
        if (typeof window.logout === 'function') {
            window.logout();
        } else {
            // Fallback: show logout modal if it exists
            const modal = document.getElementById('logoutModal');
            if (modal) {
                modal.classList.add('show');
            } else {
                // Last resort: direct logout
                localStorage.removeItem('userEmail');
                localStorage.removeItem('authToken');
                window.location.href = 'signup.html';
            }
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isMenuOpen) {
            closeMenu(hamburger, overlay, drawer);
        }
    });

    // Handle resize - close menu if switching to desktop
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if (!isMobile() && isMenuOpen) {
                closeMenu(hamburger, overlay, drawer);
            }
        }, 100);
    });
}
