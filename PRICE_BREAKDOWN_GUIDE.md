# Price Breakdown Feature - Developer Guide

## Overview

The **Price Breakdown Feature** provides transparent pricing for users during the booking flow. Instead of showing a lump sum total, Heavenly breaks down the cost into clear, understandable components with explanations for each fee.

## Architecture

### User-Facing Component

**Location**: `src/hotel-details.html` (booking card, right sidebar)

**Interaction Flow**:
```
User selects dates → Breakdown calculates → Card displays (collapsed)
                ↓ (User clicks)
           Card expands → Full details shown
```

### Key HTML Elements

1. **Price Summary** (Quick preview)
   - Class: `.price-summary`
   - Shows: Nights × price per night = total
   - Display: Always visible when dates are selected

2. **Price Breakdown Card** (Detailed breakdown)
   - Class: `.price-breakdown-card`
   - Contains: Expandable/collapsible sections
   - Toggle: Click header to expand/collapse

## Fee Configuration

Located in `src/hotel-details.html` (around line 1922):

```javascript
const FEES = {
  platformMaintenance: { 
    percent: 2,  // 2% of base stay price
    min: 0 
  },
  hostSupport: { 
    percent: 2,  // 2% of base stay price
    min: 0 
  },
  taxRate: 0.05  // 5% applied to subtotal
};
```

### Customizing Fees

**To change platform maintenance fee from 2% to 3%**:
```javascript
const FEES = {
  platformMaintenance: { percent: 3 },  // Changed from 2 to 3
  hostSupport: { percent: 2 },
  taxRate: 0.05
};
```

**To add a fixed base fee component**:
```javascript
const FEES = {
  platformMaintenance: { base: 100, percent: 1.5 },  // ₹100 fixed + 1.5%
  hostSupport: { percent: 2 },
  taxRate: 0.05
};
```

## Calculation Logic

### Function: `calculateBreakdown(basePrice, nights)`

**Input**:
- `basePrice` (number): Hotel's price per night (₹)
- `nights` (number): Number of nights selected

**Output** (object):
```javascript
{
  baseStayPrice: number,      // basePrice × nights
  platformFee: number,        // baseStayPrice × 2%
  hostSupportFee: number,     // baseStayPrice × 2%
  taxAmount: number,          // (subtotal) × 5%
  total: number,              // sum of all components
  nights: number,             // for display
  pricePerNight: number       // for display
}
```

**Calculation Steps**:
1. Base stay = basePrice × nights
2. Platform fee = baseStayPrice × (FEES.platformMaintenance.percent / 100)
3. Host support = baseStayPrice × (FEES.hostSupport.percent / 100)
4. Subtotal before tax = baseStayPrice + platformFee + hostSupportFee
5. Tax = subtotalBeforeTax × FEES.taxRate
6. **Total = baseStayPrice + platformFee + hostSupportFee + taxAmount**

### Example Calculation

```
Hotel price: ₹5,000/night
Nights: 3

Base stay = 5,000 × 3 = ₹15,000
Platform fee = 15,000 × 2% = ₹300
Host support = 15,000 × 2% = ₹300
Subtotal before tax = 15,000 + 300 + 300 = ₹15,600
Tax (5%) = 15,600 × 5% = ₹780
TOTAL = 15,000 + 300 + 300 + 780 = ₹16,380
```

## Rendering Logic

### Function: `renderPriceBreakdown(breakdown)`

**Responsibility**: Generates HTML for the breakdown card with current expansion state

**Key Features**:
- Maintains expanded/collapsed state across re-renders
- Includes descriptive subtexts for each fee
- Adds trust signal at bottom
- Attaches click handler to toggle expand/collapse

**HTML Structure Created**:
```
.price-breakdown-card
├── .breakdown-header (clickable)
│   ├── Title + Total
│   └── Toggle arrow (animated)
├── .breakdown-details (collapsible)
│   ├── .breakdown-item (base stay price)
│   ├── .breakdown-item (platform fee)
│   ├── .breakdown-item (host support)
│   ├── .breakdown-item (taxes)
│   ├── .breakdown-separator
│   ├── .breakdown-total-row (bold total)
│   └── .breakdown-trust-signal (green box)
```

## CSS Styling

All styles defined in `<style>` section (lines 780-850):

### Key Classes

| Class | Purpose |
|-------|---------|
| `.price-breakdown-card` | Main container, hidden by default |
| `.price-breakdown-card.visible` | Makes card visible with fade-in animation |
| `.breakdown-header` | Clickable toggle area |
| `.breakdown-toggle.open` | Arrow rotates 180° when expanded |
| `.breakdown-details` | Container for all items |
| `.breakdown-details.open` | Smooth max-height expansion |
| `.breakdown-item` | Individual fee line |
| `.breakdown-label-sub` | Gray helper text under main label |
| `.breakdown-trust-signal` | Green success box with checkmark |

### Animation: `@keyframes fadeIn`

```css
from {
  opacity: 0;
  transform: translateY(-8px);  /* Slides down slightly */
}
to {
  opacity: 1;
  transform: translateY(0);
}
```

## Dynamic Updates

### Trigger: `updateActionState()`

Called whenever:
- User selects/changes check-in date
- User selects/changes check-out date
- User changes guest count
- Dates become valid again after being invalid

**Flow**:
1. Check if dates are valid (start < end) and guests >= 1
2. If **valid**:
   - Enable "Book Now" button
   - Show success message
   - Calculate breakdown with `calculateBreakdown()`
   - Render card with `renderPriceBreakdown()`
   - Show price summary + breakdown card
3. If **invalid**:
   - Disable button
   - Hide summary and breakdown
   - Show instruction message

## Reset Behavior

### Function: `resetAvailability()`

Called when dates become invalid:
```javascript
function resetAvailability() {
  messageEl.style.display = 'none';
  priceSummary.style.display = 'none';
  priceBreakdownCard.style.display = 'none';  // Hide breakdown
}
```

### Function: `resetBooking()`

Called when user clicks "Book Again" after booking:
- Calls `resetAvailability()` internally
- Clears all date selections
- Resets calendar state
- Returns focus to booking card

## Integration Points

### With Calendar Component

The calendar's `getRange()` method returns selected dates:
```javascript
const { start, end } = calendarInstance.getRange();
selectedStart = start;
selectedEnd = end;
updateActionState();  // Recalculates breakdown
```

### With Guest Selector

Guest count updates also trigger recalculation:
```javascript
function handleGuestChange(newGuest) {
  guests = newGuest;
  updateActionState();  // Recalculates breakdown
}
```

## Version 2 Enhancements

The current structure is designed to support future features:

### 1. Per-Property Custom Fees

```javascript
// Could load from API based on hotel ID
const FEES = await fetchHotelFees(hotelId);

// Each hotel could have unique rates
const breakdown = calculateBreakdown(hotel.price, nights);
```

**Benefit**: Hotels in different regions/categories pay different rates

### 2. Host Earnings Dashboard

```javascript
// Version 2: Show hosts what THEY earn vs what platform keeps
function calculateHostEarnings(breakdown) {
  return {
    hostReceives: breakdown.baseStayPrice - breakdown.platformFee,
    platformKeeps: breakdown.platformFee + breakdown.hostSupportFee,
    taxesPassed: breakdown.taxAmount  // Usually passed to government
  };
}
```

### 3. Promotional Discounts

```javascript
function calculateBreakdown(basePrice, nights, discountPercent = 0) {
  let baseStayPrice = basePrice * nights;
  
  // Apply discount to base price
  if (discountPercent > 0) {
    baseStayPrice = baseStayPrice * (1 - discountPercent / 100);
  }
  
  // Rest of calculation continues...
}
```

## Testing Checklist

- [ ] Select different date ranges (1 night, 5 nights, 30 nights)
- [ ] Verify calculation accuracy for each breakdown
- [ ] Toggle expand/collapse smoothly
- [ ] Change dates while expanded (breakdown updates)
- [ ] Mobile view: breakdown card remains readable
- [ ] Trust signal displays in all scenarios
- [ ] Total always equals sum of components (no floating point errors)
- [ ] After rebooking: breakdown resets and recalculates correctly

## Common Issues & Solutions

### Breakdown Not Showing

**Symptom**: Card never appears even when dates selected

**Solution**: Check that dates are actually valid:
- `selectedStart` and `selectedEnd` must be non-null
- `selectedEnd > selectedStart` (end date after start)
- `guests >= 1`

### Numbers Show as Decimals

**Symptom**: Breakdown shows ₹5000.5 instead of ₹5001

**Solution**: All values must be wrapped in `Math.round()`:
```javascript
const platformFee = Math.round(baseStayPrice * 0.02);  // Correct
// NOT: baseStayPrice * 0.02  // Wrong
```

### Breakdown Doesn't Update When Dates Change

**Symptom**: Card shows old values even after new dates selected

**Solution**: Ensure `updateActionState()` is called:
```javascript
// In date selection handler:
selectedStart = newDate;
updateActionState();  // Must call this
```

### Toggle Arrow Rotates But Content Doesn't Expand

**Symptom**: `.breakdown-details.open` class not being applied

**Solution**: Verify the click handler in `renderPriceBreakdown()`:
```javascript
const header = priceBreakdownCard.querySelector('.breakdown-header');
header.addEventListener('click', () => {
  const details = priceBreakdownCard.querySelector('.breakdown-details');
  details.classList.toggle('open');  // This line must execute
});
```

## Accessibility Notes

- ✅ Using semantic HTML (`<span>`, `<div>` roles clear from context)
- ✅ Color contrast: Black text on white (7:1 ratio, WCAG AAA)
- ✅ Green trust signal: Not color-only (includes checkmark icon)
- ✅ Expandable section: Click area is large (full header width)
- ⚠️ **Future**: Add `aria-expanded` attribute to toggle
- ⚠️ **Future**: Add `aria-label` for screen readers

## References

- Main implementation: `src/hotel-details.html` (lines 1920-2010)
- CSS styles: `src/hotel-details.html` (lines 780-850)
- Calculation logic: `~functions.calculateBreakdown()`
- Integration: `~updateActionState()`
