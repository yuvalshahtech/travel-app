# Price Breakdown Feature - Test Scenarios

## Quick Test Guide

Test the Price Breakdown feature with these scenarios to ensure it's working correctly.

---

## Scenario 1: Basic Single Night Booking

### Steps:
1. Open `src/home.html` (or navigate to a hotel detail page)
2. Click on any hotel card to view details
3. In the **Booking Card** (right sidebar):
   - Click on "Check-in" date field
   - Select today's date
   - Select tomorrow's date for "Check-out"
   - Keep guests at 1

### Expected Result:
✅ A blue "Ready to book!" message appears  
✅ Price summary shows: "**1 nights** × ₹[price] per night"  
✅ Price breakdown card appears below with toggle header  
✅ Breakdown shows: Base (₹), Platform Fee (₹), Host Support (₹), Tax (₹), **Total (₹)**

### Verification:
- Base Stay Price = ₹[hotel.price] × 1 night
- Platform Fee = Base × 2%
- Host Support = Base × 2%
- Tax = (Base + Platform + Support) × 5%
- Total = Base + Platform + Support + Tax

---

## Scenario 2: Multi-Night with Expansion

### Steps:
1. From the hotel details page:
   - Select check-in: 5 days from today
   - Select check-out: 12 days from today (7 nights)
   - Keep guests at 1

### Expected Result:
✅ Price summary shows: "**7 nights** × ₹[price] per night"  
✅ Breakdown card displays **collapsed** by default  
✅ Only "Price Breakdown" title + total amount shown  
✅ Click anywhere on the header → card **expands smoothly**  
✅ All 4 fee items are now visible with descriptions  
✅ Click header again → card **collapses smoothly**

### Verification:
- All calculations use 7 nights
- Toggle arrow rotates 180° when expanding
- No visual jumps or flickering on expand/collapse

---

## Scenario 3: Dynamic Update (Changing Dates)

### Steps:
1. Hotel details page with dates already selected (as in Scenario 2)
2. **While breakdown is expanded**, click on the calendar again
3. Change check-out date from day 12 to day 15 (now 10 nights)

### Expected Result:
✅ Price breakdown **updates instantly**  
✅ Shows: "**10 nights**" × ₹[price]  
✅ All fees recalculate automatically  
✅ Breakdown remains **expanded** (state preserved)  
✅ Total amount in header updates immediately  
✅ All values in expanded view update correctly

### Verification:
- Base Stay Price = ₹[price] × 10 (not 7)
- All dependent fees recalculate based on new base
- Total increases proportionally
- No need to re-expand to see changes

---

## Scenario 4: Invalid Date Selection

### Steps:
1. On hotel details page:
   - Select check-in date: tomorrow
   - Select check-out date: tomorrow (same as check-in)

### Expected Result:
✅ Red error message: "Select dates to continue"  
✅ Price summary **disappears**  
✅ Breakdown card **disappears**  
✅ "Book Now" button **disabled** (grayed out)

### Verification:
- No calculation shown for invalid range
- UI clearly indicates dates are invalid
- Button cannot be clicked (disabled state)

---

## Scenario 5: Guest Count Changes

### Steps:
1. Hotel details with valid dates selected (3 nights, 1 guest)
2. Click + button in guest selector to increase to 3 guests
3. Observe the breakdown

### Expected Result:
✅ Breakdown **updates immediately**  
✅ All calculations remain **the same** (guest count doesn't affect pricing)  
✅ Only the total displayed updates if refreshed  
✅ Confirms pricing is nightly, not per-guest

---

## Scenario 6: On Mobile Device

### Steps:
1. Open hotel details on mobile/tablet view
2. Scroll to booking card (right sidebar becomes single column)
3. Select dates as in Scenario 1

### Expected Result:
✅ Price breakdown card **fully visible** on mobile  
✅ Text is **readable** (not cut off)  
✅ Toggle button works smoothly on tap  
✅ Card expands to show all details without overflow  
✅ Trust signal ("✓ No hidden charges...") displays completely

### Verification:
- No horizontal scrolling needed
- All numbers visible with proper spacing
- Tap areas are large enough (min 44x44px)

---

## Scenario 7: Rebooking (Book Again Flow)

### Steps:
1. Complete a booking and see "Booking Confirmed!" message
2. Click "Book this hotel again"
3. On the new booking panel:
   - Select new dates (e.g., 2 nights)
   - View the breakdown

### Expected Result:
✅ Breakdown card is **reset** (original state)  
✅ Shows new calculation for 2 nights  
✅ No values from previous booking remain  
✅ All form fields are **empty/reset**

---

## Scenario 8: Visual Consistency

### Steps:
1. Go back to home page (home.html)
2. Navigate to 3 different hotels' detail pages
3. On each, select dates and view breakdown

### Expected Result:
✅ Breakdown card looks **identical** across all pages  
✅ Colors are consistent (white background, green trust signal)  
✅ Typography is consistent (fees bold, descriptions gray)  
✅ Fee structure is **identical** (2%/2%/5% on all)  
✅ Indian Rupee formatting (₹ symbol, comma separators) consistent

---

## Scenario 9: Calculation Accuracy

### Test Case A: ₹5,000/night for 3 nights

```
Expected:
- Base: ₹15,000 (5,000 × 3)
- Platform: ₹300 (15,000 × 2%)
- Host: ₹300 (15,000 × 2%)
- Subtotal before tax: ₹15,600
- Tax: ₹780 (15,600 × 5%)
- TOTAL: ₹16,380
```

### Test Case B: ₹2,000/night for 5 nights

```
Expected:
- Base: ₹10,000 (2,000 × 5)
- Platform: ₹200 (10,000 × 2%)
- Host: ₹200 (10,000 × 2%)
- Subtotal before tax: ₹10,400
- Tax: ₹520 (10,400 × 5%)
- TOTAL: ₹10,920
```

### Verification Steps:
1. Find hotels with ₹5,000 and ₹2,000 prices
2. Perform bookings matching test cases
3. Verify each line item matches expected values
4. Confirm total equals sum of all components

---

## Scenario 10: Accessibility (Screen Reader)

### Tools Needed:
- NVDA (Windows) or VoiceOver (Mac)

### Steps:
1. Enable screen reader
2. Navigate to hotel details page
3. Select dates in calendar
4. Activate screen reader's virtual cursor on booking card

### Expected Behavior:
✅ Screen reader announces "Price Breakdown" as heading  
✅ Each fee item is read in order (Base, Platform, Host, Tax)  
✅ Descriptions read clearly (e.g., "Platform Maintenance Fee, 2% of base stay")  
✅ Total is clearly announced  
✅ Trust signal is read as "(checkmark) No hidden charges..."

### Future Enhancement:
- Add `aria-expanded` attribute to toggle header for clarity
- Add `role="tabpanel"` to details section

---

## Browser Compatibility Test

Test in these browsers to ensure feature works everywhere:

| Browser | Windows | Mac | Mobile |
|---------|---------|-----|--------|
| Chrome | ✓ | ✓ | ✓ |
| Firefox | ✓ | ✓ | ✓ |
| Safari | ✓ | ✓ | ✓ |
| Edge | ✓ | - | ✓ |

### Known Limitations:
- **IE 11**: Not supported (uses modern CSS/JS features)
- **Mobile Safari**: Test on iOS 12+

---

## Performance Test

### Steps:
1. Open browser DevTools (F12)
2. Go to Network tab
3. Navigate to hotel details
4. Select dates rapidly (quick clicks)
5. Toggle breakdown expand/collapse repeatedly

### Expected Results:
✅ No lag when selecting dates  
✅ Breakdown renders instantly (<100ms)  
✅ Toggle animation is smooth (60fps)  
✅ No JavaScript errors in console  
✅ Network tab shows no unexpected requests

---

## Checklist for Feature Release

- [ ] All 10 scenarios pass
- [ ] No JavaScript errors in console
- [ ] Mobile view fully functional
- [ ] Trust signal displays on all pages
- [ ] Calculations verified for accuracy
- [ ] CSS animations smooth on all browsers
- [ ] README updated with feature description
- [ ] Developer guide available (PRICE_BREAKDOWN_GUIDE.md)
- [ ] Code is commented for maintainability
- [ ] No hard-coded values (all fees configurable)

---

## Reporting Issues

If any test scenario fails:

1. **Note the browser/device** used
2. **Screenshot** the bug (including console errors)
3. **Describe expected vs actual** behavior
4. **Try clearing cache** (Ctrl+Shift+Del) and retry
5. **Check console errors** (F12 → Console tab)

Common fixes:
- Clear browser cache and reload
- Check that `.env` file is configured
- Verify backend server is running (`uvicorn main:app --reload`)
- Restart the development server
