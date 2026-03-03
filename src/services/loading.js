/**
 * Branded Loading Component - Reusable loading state for Heavenly Travel
 * 
 * Usage:
 *   import { createLoadingHTML, injectLoadingStyles, getLogoUrl } from './services/loading.js';
 *   
 *   // Inject styles once on page load
 *   injectLoadingStyles();
 *   
 *   // Use in any container
 *   container.innerHTML = createLoadingHTML('Finding heavenly stays...');
 */

// Get the logo URL based on current environment
export function getLogoUrl() {
    const apiBase = (typeof window !== 'undefined' && window.__API_BASE__) 
        ? window.__API_BASE__ 
        : 'https://travel-app-96ld.onrender.com';
    return `${apiBase}/uploads/logo/heavenly_logo_png.png`;
}

/**
 * Create branded loading HTML with logo, spinner, and message
 * @param {string} message - Loading message to display
 * @returns {string} HTML string for loading component
 */
export function createLoadingHTML(message = 'Finding heavenly stays for you...') {
    const logoUrl = getLogoUrl();
    return `
        <div class="heavenly-loading">
            <div class="heavenly-loading__logo-container">
                <img src="${logoUrl}" alt="Heavenly" class="heavenly-loading__logo" />
            </div>
            <div class="heavenly-loading__spinner"></div>
            <p class="heavenly-loading__message">${message}</p>
        </div>
    `;
}

/**
 * CSS styles for the loading component
 * Includes animations: fade-in, spinner rotation, subtle logo bounce
 */
const loadingStyles = `
/* Heavenly Branded Loading Component */
.heavenly-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 20px;
    padding: 60px 20px;
    min-height: 200px;
    animation: heavenlyFadeIn 0.4s ease-out;
}

.heavenly-loading__logo-container {
    position: relative;
    animation: heavenlyLogoBounce 2s ease-in-out infinite;
}

.heavenly-loading__logo {
    height: 56px;
    width: auto;
    object-fit: contain;
    filter: drop-shadow(0 4px 12px rgba(255, 90, 95, 0.15));
}

.heavenly-loading__spinner {
    width: 36px;
    height: 36px;
    border: 3px solid #f0f0f0;
    border-top-color: #FF5A5F;
    border-radius: 50%;
    animation: heavenlySpinner 0.8s linear infinite;
}

.heavenly-loading__message {
    font-size: 15px;
    font-weight: 500;
    color: #666;
    margin: 0;
    text-align: center;
    letter-spacing: 0.2px;
    animation: heavenlyTextPulse 2s ease-in-out infinite;
}

/* Animations */
@keyframes heavenlyFadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes heavenlySpinner {
    to {
        transform: rotate(360deg);
    }
}

@keyframes heavenlyLogoBounce {
    0%, 100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-6px);
    }
}

@keyframes heavenlyTextPulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.6;
    }
}

/* Responsive adjustments */
@media (max-width: 480px) {
    .heavenly-loading {
        padding: 40px 16px;
        gap: 16px;
    }
    
    .heavenly-loading__logo {
        height: 44px;
    }
    
    .heavenly-loading__spinner {
        width: 28px;
        height: 28px;
    }
    
    .heavenly-loading__message {
        font-size: 14px;
    }
}

/* Compact variant for inline use */
.heavenly-loading--compact {
    padding: 30px 16px;
    gap: 14px;
    min-height: 120px;
}

.heavenly-loading--compact .heavenly-loading__logo {
    height: 40px;
}

.heavenly-loading--compact .heavenly-loading__spinner {
    width: 28px;
    height: 28px;
    border-width: 2px;
}

.heavenly-loading--compact .heavenly-loading__message {
    font-size: 13px;
}
`;

let stylesInjected = false;

/**
 * Inject loading component styles into the document
 * Safe to call multiple times - only injects once
 */
export function injectLoadingStyles() {
    if (stylesInjected || typeof document === 'undefined') return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'heavenly-loading-styles';
    styleEl.textContent = loadingStyles;
    document.head.appendChild(styleEl);
    stylesInjected = true;
}

/**
 * Create compact loading HTML for smaller containers
 * @param {string} message - Loading message to display
 * @returns {string} HTML string for compact loading component
 */
export function createCompactLoadingHTML(message = 'Loading...') {
    const logoUrl = getLogoUrl();
    return `
        <div class="heavenly-loading heavenly-loading--compact">
            <div class="heavenly-loading__logo-container">
                <img src="${logoUrl}" alt="Heavenly" class="heavenly-loading__logo" />
            </div>
            <div class="heavenly-loading__spinner"></div>
            <p class="heavenly-loading__message">${message}</p>
        </div>
    `;
}
