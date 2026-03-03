/**
 * Pricing Module - Centralized pricing calculations for the travel app
 * 
 * This module contains all pricing logic used across the frontend.
 * All prices are calculated including:
 * - Room charges (base price × nights)
 * - Cleaning fee (fixed ₹500)
 * - Platform service fee (10% of subtotal)
 * - GST (18% of subtotal + platform fee)
 */

// Fixed fee constants
const CLEANING_FEE = 500;
const PLATFORM_FEE_RATE = 0.10;
const GST_RATE = 0.18;

/**
 * Calculate full price breakdown including all fees and taxes
 * @param {number} pricePerNight - Base price per night from hotel
 * @param {number} nights - Number of nights (default: 1)
 * @returns {Object} Breakdown with roomCharges, cleaningFee, platformFee, gst, total
 */
export function calculateBreakdown(pricePerNight, nights = 1) {
    const roomCharges = pricePerNight * nights;
    const cleaningFee = CLEANING_FEE;
    const subtotal = roomCharges + cleaningFee;
    const platformFee = subtotal * PLATFORM_FEE_RATE;
    const subtotalBeforeGST = subtotal + platformFee;
    const gst = subtotalBeforeGST * GST_RATE;
    const total = subtotal + platformFee + gst;

    return {
        roomCharges: Math.round(roomCharges),
        cleaningFee: Math.round(cleaningFee),
        platformFee: Math.round(platformFee),
        gst: Math.round(gst),
        total: Math.round(total)
    };
}

/**
 * Calculate total payable price for display (1 night)
 * Use this for hotel cards and list views
 * @param {number} pricePerNight - Base price per night from hotel
 * @returns {number} Total price including all fees and taxes for 1 night
 */
export function calculateDisplayPrice(pricePerNight) {
    return calculateBreakdown(pricePerNight, 1).total;
}

/**
 * Format amount as Indian currency
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency string (e.g., "₹12,500")
 */
export function formatCurrency(amount) {
    return '₹' + Math.round(amount).toLocaleString('en-IN');
}

/**
 * Format price per night for display with label
 * @param {number} pricePerNight - Base price per night
 * @returns {string} Formatted string (e.g., "₹12,500 / night")
 */
export function formatPricePerNight(pricePerNight) {
    const total = calculateDisplayPrice(pricePerNight);
    return formatCurrency(total) + ' / night';
}

/**
 * Get formatted display price (total for 1 night)
 * @param {number} pricePerNight - Base price per night
 * @returns {string} Formatted currency string
 */
export function getFormattedDisplayPrice(pricePerNight) {
    return formatCurrency(calculateDisplayPrice(pricePerNight));
}
