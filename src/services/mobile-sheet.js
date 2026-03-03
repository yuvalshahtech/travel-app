/**
 * Mobile Bottom Sheet Module - Draggable bottom sheet for map-first UX
 * 
 * Usage:
 *   import { initMobileSheet, injectMobileSheetStyles } from './services/mobile-sheet.js';
 *   injectMobileSheetStyles();
 *   initMobileSheet({
 *       sheetSelector: '.list-container',
 *       mapSelector: '#map'
 *   });
 * 
 * Only activates on mobile (max-width: 768px)
 */

const MOBILE_BREAKPOINT = 768;

// Snap states (percentage of viewport height)
const SNAP_STATES = {
    COLLAPSED: 0.25,    // 25% height
    HALF: 0.60,         // 60% height (default)
    EXPANDED: 0.95      // 95% height
};

const DRAG_THRESHOLD = 50; // Minimum drag distance to trigger snap

/**
 * CSS styles for mobile bottom sheet
 */
const mobileSheetStyles = `
/* ============================================
   MOBILE BOTTOM SHEET - Only visible <= 768px
   ============================================ */

/* Drag handle indicator */
.mobile-sheet-handle {
    display: none;
    width: 40px;
    height: 4px;
    background: #ddd;
    border-radius: 2px;
    margin: 12px auto 8px;
    cursor: grab;
}

.mobile-sheet-handle:active {
    cursor: grabbing;
}

/* Sheet header with drag area */
.mobile-sheet-header {
    display: none;
    padding: 0 16px 12px;
    background: #fff;
    border-radius: 20px 20px 0 0;
    touch-action: none;
    user-select: none;
}

/* ============================================
   MOBILE MEDIA QUERY - SEARCH PAGE
   ============================================ */
@media (max-width: 768px) {
    /* Make container fill screen for map-first */
    .container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        height: 100dvh;
        padding: 0 !important;
        position: relative;
        overflow: hidden;
    }

    /* Map takes full screen */
    .map-container {
        position: fixed !important;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100% !important;
        height: 100% !important;
        z-index: 1;
    }

    #map {
        width: 100% !important;
        height: 100% !important;
    }

    /* List container becomes bottom sheet */
    .list-container {
        position: fixed !important;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 100;
        background: #fff;
        border-radius: 20px 20px 0 0;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        will-change: transform;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        max-height: 95vh;
        max-height: 95dvh;
    }

    /* Show sheet header with drag handle on mobile */
    .mobile-sheet-header {
        display: block;
        flex-shrink: 0;
    }

    .mobile-sheet-handle {
        display: block;
    }

    /* Hotel list header adjustments */
    .hotel-list-header {
        padding: 0 16px 12px !important;
        flex-shrink: 0;
    }

    /* Scrollable hotel list */
    #hotelList {
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: contain;
        padding-bottom: 20px;
    }

    /* Hotel count styling */
    .hotel-count {
        padding: 0 16px 8px !important;
        flex-shrink: 0;
    }

    /* Prevent body scroll when sheet is being dragged */
    body.sheet-dragging {
        overflow: hidden;
        touch-action: none;
    }

    /* Header adjustments for mobile */
    header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 200;
        background: #fff;
    }

    /* Add padding to prevent header overlap */
    body {
        padding-top: 70px;
    }

    /* Filter button on mobile */
    .filters-btn {
        position: fixed;
        bottom: auto;
        top: 80px;
        right: 16px;
        z-index: 150;
        background: #fff;
        border-radius: 24px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
    }

    /* Search input in header */
    .search-bar {
        flex: 1;
        max-width: none;
        margin: 0 8px;
    }
}

/* Sheet state classes */
.mobile-sheet--collapsed {
    transform: translateY(calc(100% - 25vh)) !important;
}

.mobile-sheet--half {
    transform: translateY(calc(100% - 60vh)) !important;
}

.mobile-sheet--expanded {
    transform: translateY(calc(100% - 95vh)) !important;
}

/* Disable transitions during drag */
.mobile-sheet--dragging {
    transition: none !important;
}
`;

let stylesInjected = false;
let sheetInstance = null;

/**
 * Inject mobile sheet styles
 */
export function injectMobileSheetStyles() {
    if (stylesInjected || typeof document === 'undefined') return;

    const styleEl = document.createElement('style');
    styleEl.id = 'mobile-sheet-styles';
    styleEl.textContent = mobileSheetStyles;
    document.head.appendChild(styleEl);
    stylesInjected = true;
}

/**
 * Mobile Sheet Controller Class
 */
class MobileSheetController {
    constructor(options = {}) {
        this.sheet = document.querySelector(options.sheetSelector || '.list-container');
        this.map = document.querySelector(options.mapSelector || '#map');
        this.hotelList = document.querySelector('#hotelList');

        if (!this.sheet) {
            console.warn('MobileSheet: Sheet container not found');
            return;
        }

        this.currentState = 'half'; // Default state
        this.isDragging = false;
        this.startY = 0;
        this.currentY = 0;
        this.sheetHeight = 0;
        this.viewportHeight = window.innerHeight;

        this.init();
    }

    init() {
        // Create and inject sheet header with drag handle
        this.createSheetHeader();

        // Set initial state
        this.setState('half', false);

        // Bind touch events
        this.bindEvents();

        // Handle resize
        this.handleResize();
    }

    createSheetHeader() {
        // Check if header already exists
        if (this.sheet.querySelector('.mobile-sheet-header')) return;

        const header = document.createElement('div');
        header.className = 'mobile-sheet-header';
        header.innerHTML = `<div class="mobile-sheet-handle"></div>`;

        // Insert at the beginning of sheet
        this.sheet.insertBefore(header, this.sheet.firstChild);

        this.dragHandle = header;
    }

    bindEvents() {
        // Touch events on drag handle
        this.dragHandle.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: true });
        this.dragHandle.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
        this.dragHandle.addEventListener('touchend', this.onTouchEnd.bind(this), { passive: true });

        // Also allow dragging from hotel list header
        const listHeader = this.sheet.querySelector('.hotel-list-header');
        if (listHeader) {
            listHeader.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: true });
            listHeader.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
            listHeader.addEventListener('touchend', this.onTouchEnd.bind(this), { passive: true });
        }

        // Handle scroll-triggered state changes
        if (this.hotelList) {
            this.hotelList.addEventListener('scroll', this.onListScroll.bind(this), { passive: true });
            this.hotelList.addEventListener('touchstart', this.onListTouchStart.bind(this), { passive: true });
            this.hotelList.addEventListener('touchmove', this.onListTouchMove.bind(this), { passive: false });
            this.hotelList.addEventListener('touchend', this.onListTouchEnd.bind(this), { passive: true });
        }

        // Resize handler
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }

    onTouchStart(e) {
        if (window.innerWidth > MOBILE_BREAKPOINT) return;

        this.isDragging = true;
        this.startY = e.touches[0].clientY;
        this.currentY = this.startY;
        this.sheetStartTransform = this.getSheetTransformY();

        this.sheet.classList.add('mobile-sheet--dragging');
        document.body.classList.add('sheet-dragging');
    }

    onTouchMove(e) {
        if (!this.isDragging || window.innerWidth > MOBILE_BREAKPOINT) return;

        this.currentY = e.touches[0].clientY;
        const deltaY = this.currentY - this.startY;

        // Calculate new transform
        const newTransform = this.sheetStartTransform + deltaY;

        // Clamp to valid range
        const minTransform = this.viewportHeight * (1 - SNAP_STATES.EXPANDED);
        const maxTransform = this.viewportHeight * (1 - SNAP_STATES.COLLAPSED);

        const clampedTransform = Math.max(minTransform, Math.min(maxTransform, newTransform));

        // Apply transform using requestAnimationFrame
        requestAnimationFrame(() => {
            this.sheet.style.transform = `translateY(${clampedTransform}px)`;
        });

        e.preventDefault();
    }

    onTouchEnd(e) {
        if (!this.isDragging || window.innerWidth > MOBILE_BREAKPOINT) return;

        this.isDragging = false;
        this.sheet.classList.remove('mobile-sheet--dragging');
        document.body.classList.remove('sheet-dragging');

        const deltaY = this.currentY - this.startY;

        // Determine which state to snap to
        if (Math.abs(deltaY) < DRAG_THRESHOLD) {
            // Small drag - stay in current state
            this.setState(this.currentState);
            return;
        }

        if (deltaY > 0) {
            // Dragged down - collapse
            if (this.currentState === 'expanded') {
                this.setState('half');
            } else if (this.currentState === 'half') {
                this.setState('collapsed');
            } else {
                this.setState('collapsed');
            }
        } else {
            // Dragged up - expand
            if (this.currentState === 'collapsed') {
                this.setState('half');
            } else if (this.currentState === 'half') {
                this.setState('expanded');
            } else {
                this.setState('expanded');
            }
        }
    }

    // List scroll handling for natural behavior
    listScrollTop = 0;
    listTouchStartY = 0;
    isListAtTop = true;
    isListAtBottom = false;

    onListScroll(e) {
        if (window.innerWidth > MOBILE_BREAKPOINT) return;

        this.listScrollTop = this.hotelList.scrollTop;
        this.isListAtTop = this.listScrollTop <= 0;
        this.isListAtBottom = this.hotelList.scrollHeight - this.hotelList.scrollTop <= this.hotelList.clientHeight + 5;
    }

    onListTouchStart(e) {
        if (window.innerWidth > MOBILE_BREAKPOINT) return;

        this.listTouchStartY = e.touches[0].clientY;
        this.listScrollTop = this.hotelList.scrollTop;
        this.isListAtTop = this.listScrollTop <= 0;
        this.isListAtBottom = this.hotelList.scrollHeight - this.hotelList.scrollTop <= this.hotelList.clientHeight + 5;
    }

    onListTouchMove(e) {
        if (window.innerWidth > MOBILE_BREAKPOINT) return;

        const currentY = e.touches[0].clientY;
        const deltaY = currentY - this.listTouchStartY;

        // If at top and pulling down, collapse sheet
        if (this.isListAtTop && deltaY > DRAG_THRESHOLD && this.currentState !== 'collapsed') {
            e.preventDefault();
            if (this.currentState === 'expanded') {
                this.setState('half');
            } else {
                this.setState('collapsed');
            }
            return;
        }

        // If at bottom and pushing up, expand sheet
        if (this.isListAtBottom && deltaY < -DRAG_THRESHOLD && this.currentState !== 'expanded') {
            e.preventDefault();
            if (this.currentState === 'collapsed') {
                this.setState('half');
            } else {
                this.setState('expanded');
            }
            return;
        }
    }

    onListTouchEnd(e) {
        // Reset tracking
    }

    getSheetTransformY() {
        const transform = window.getComputedStyle(this.sheet).transform;
        if (transform === 'none') {
            return this.viewportHeight * (1 - SNAP_STATES.HALF);
        }
        const matrix = new DOMMatrix(transform);
        return matrix.m42;
    }

    setState(state, animate = true) {
        this.currentState = state;

        // Remove all state classes
        this.sheet.classList.remove('mobile-sheet--collapsed', 'mobile-sheet--half', 'mobile-sheet--expanded');

        // Clear inline transform
        this.sheet.style.transform = '';

        // Apply state class
        this.sheet.classList.add(`mobile-sheet--${state}`);

        // Update map interaction hint
        if (this.map) {
            if (state === 'collapsed') {
                this.map.style.pointerEvents = 'auto';
            } else {
                this.map.style.pointerEvents = 'auto';
            }
        }
    }

    handleResize() {
        this.viewportHeight = window.innerHeight;

        // If switching to desktop, reset styles
        if (window.innerWidth > MOBILE_BREAKPOINT) {
            this.sheet.classList.remove('mobile-sheet--collapsed', 'mobile-sheet--half', 'mobile-sheet--expanded', 'mobile-sheet--dragging');
            this.sheet.style.transform = '';
            document.body.classList.remove('sheet-dragging');
        } else {
            // Re-apply current state
            this.setState(this.currentState, false);
        }
    }

    // Public method to collapse sheet (useful when map marker clicked)
    collapse() {
        this.setState('collapsed');
    }

    // Public method to expand to half
    expandHalf() {
        this.setState('half');
    }

    // Public method to fully expand
    expand() {
        this.setState('expanded');
    }
}

/**
 * Initialize mobile sheet
 * @param {Object} options - Configuration options
 */
export function initMobileSheet(options = {}) {
    if (typeof window === 'undefined') return null;

    // Only initialize on mobile
    if (window.innerWidth > MOBILE_BREAKPOINT) {
        // Still create instance to handle resize
        sheetInstance = new MobileSheetController(options);
        return sheetInstance;
    }

    sheetInstance = new MobileSheetController(options);
    return sheetInstance;
}

/**
 * Get sheet instance for external control
 */
export function getSheetInstance() {
    return sheetInstance;
}
