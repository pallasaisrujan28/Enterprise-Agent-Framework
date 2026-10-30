# Quick Testing Guide - Teams-Style Group Chat

## 🚀 Start the System

### 1. Start Backend (Terminal 1)
```bash
cd "/Users/Saisrujan/Downloads/Synthetic Data/backend"
uvicorn main:app --reload --port 8010
```

**Expected Output:**
```
INFO:     Uvicorn running on http://localhost:8010
INFO:     Application startup complete.
```

### 2. Start Frontend (Terminal 2)
```bash
cd "/Users/Saisrujan/Downloads/Synthetic Data/frontend"
npm run dev
```

**Expected Output:**
```
  ▲ Next.js 15.4.6
  - Local:        http://localhost:3010
```

---

## 📋 Testing Checklist

### Phase 1: Basic UI Testing
- [ ] Open `http://localhost:3010`
- [ ] Navigate to Synthetic Audience Store (`/synthetic-audience`)
- [ ] Verify audience groups are displayed as cards
- [ ] Each card shows:
  - [ ] Segment name
  - [ ] Campaign context
  - [ ] Persona count badge
  - [ ] "Chat with Group" button
  - [ ] "View Personas" button

### Phase 2: Group Chat Testing
- [ ] Click "Chat with Group" button
- [ ] **Verify GroupChatDialog opens:**
  - [ ] Dialog appears (max-w-6xl, 80vh height)
  - [ ] Header shows group name and context
  - [ ] Participants sidebar visible on left (280px width)
  - [ ] All personas listed with avatars
  - [ ] Chat area empty with welcome message
  - [ ] Message input box at bottom
  - [ ] Media upload button (camera icon)
  - [ ] Send button

### Phase 3: Group Chat Functionality
- [ ] **Test Text Message:**
  - [ ] Type message in input box
  - [ ] Click Send
  - [ ] Verify user message appears (blue bubble, right-aligned)
  - [ ] Verify "Loading..." indicator appears
  - [ ] Verify personas respond one-by-one with delays
  - [ ] Check staggered animation (500ms between personas)
  - [ ] Verify chat auto-scrolls to bottom

- [ ] **Test Media Upload:**
  - [ ] Click media upload button (camera icon)
  - [ ] Select an image file
  - [ ] Verify preview appears above input
  - [ ] Type message
  - [ ] Click Send
  - [ ] Verify user message shows image + text
  - [ ] Verify personas respond mentioning the image
  - [ ] Check media analysis works (Claude Vision)

### Phase 4: Individual Chat Testing
- [ ] **Click Persona in Sidebar:**
  - [ ] Click any persona avatar in participants sidebar
  - [ ] Verify group chat closes
  - [ ] Verify IndividualPersonaChat dialog opens
  - [ ] Check persona name and info in header
  - [ ] Verify chat area is empty (new conversation)
  - [ ] Check media upload button present
  - [ ] Check send button present

- [ ] **Test 1-on-1 Conversation:**
  - [ ] Type message in individual chat
  - [ ] Click Send
  - [ ] Verify user message appears
  - [ ] Verify single persona response
  - [ ] Check authentic persona voice (based on traits)
  - [ ] Upload media in 1-on-1 chat
  - [ ] Verify media analysis works

### Phase 5: UI/UX Testing
- [ ] **Participants Sidebar:**
  - [ ] Click collapse button (if implemented)
  - [ ] Verify sidebar collapses/expands
  - [ ] Check hover effects on persona avatars
  - [ ] Verify scrolling if many personas

- [ ] **Dialog Controls:**
  - [ ] Click X button to close group chat
  - [ ] Click outside dialog to close (if enabled)
  - [ ] Re-open chat and verify state reset
  - [ ] Check maximize/minimize button (individual chat)

- [ ] **Message Display:**
  - [ ] Verify user messages right-aligned, blue
  - [ ] Verify persona messages left-aligned, gray
  - [ ] Check avatars show for persona messages
  - [ ] Verify timestamps display
  - [ ] Check message animations (Framer Motion)

### Phase 6: Error Handling
- [ ] **Test Empty Message:**
  - [ ] Try sending empty message
  - [ ] Verify Send button disabled

- [ ] **Test Large Media:**
  - [ ] Upload very large image/video
  - [ ] Check loading indicator
  - [ ] Verify timeout handling

- [ ] **Test Backend Offline:**
  - [ ] Stop backend server
  - [ ] Try sending message
  - [ ] Verify error message shows
  - [ ] Restart backend and retry

---

## 🔍 What to Look For

### ✅ Good Signs
- Group chat opens smoothly
- Participants sidebar shows all personas
- Messages appear with smooth animations
- Personas respond one-by-one (not all at once)
- Media upload preview works
- Individual chat opens when clicking persona
- Chat auto-scrolls to latest message
- Loading indicators show during processing

### ❌ Red Flags
- Dialog doesn't open
- Participants sidebar empty
- All persona responses appear instantly (no stagger)
- Media upload doesn't work
- Individual chat doesn't open
- Chat doesn't scroll
- Console errors visible

---

## 🐛 Common Issues & Fixes

### Issue: "Failed to fetch" error
**Fix:** Verify backend running on port 8010
```bash
curl http://localhost:8010/api/health
```

### Issue: Personas not responding
**Fix:** Check backend logs for AWS Bedrock errors
```bash
# In backend terminal, look for errors
```

### Issue: Media upload fails
**Fix:** Check file size and format
- Max size: ~10MB
- Formats: image/*, video/*

### Issue: TypeScript errors in VS Code
**Fix:** These are normal for TSX files, ignore them

### Issue: Dialog doesn't open
**Fix:** Check browser console for import errors
- Verify GroupChatDialog imported
- Verify IndividualPersonaChat imported

---

## 📊 Expected Behavior

### Group Chat Flow:
```
User clicks "Chat with Group"
   ↓
Dialog opens with sidebar + chat area
   ↓
User types "What do you think of this product?" + uploads image
   ↓
User clicks Send
   ↓
User message appears (blue bubble with image)
   ↓
"Loading..." indicator shows
   ↓
Persona 1 responds (gray bubble with avatar)
   ↓
Wait 500ms
   ↓
Persona 2 responds
   ↓
Wait 500ms
   ↓
...continue for all personas
   ↓
Chat auto-scrolls to bottom
```

### Individual Chat Flow:
```
User clicks persona in sidebar
   ↓
Group chat closes
   ↓
Individual chat dialog opens
   ↓
Persona info shown in header
   ↓
User types message
   ↓
Persona responds (single response)
   ↓
Conversation continues 1-on-1
```

---

## 🎯 Success Criteria

**Test is SUCCESSFUL if:**
- ✅ Group chat opens with Teams-style sidebar
- ✅ Personas respond one-by-one with visible delays
- ✅ Media upload works in group chat
- ✅ Clicking persona opens 1-on-1 chat popup
- ✅ Individual chat works with media support
- ✅ All animations smooth and professional
- ✅ No console errors
- ✅ Old template evaluation UI completely removed

**Test FAILS if:**
- ❌ All personas respond at once (no stagger)
- ❌ Individual chat doesn't open
- ❌ Media upload broken
- ❌ Console shows errors
- ❌ Old evaluation UI still visible

---

## 📝 Test Report Template

```
# Teams-Style Chat Test Report
Date: _______________
Tester: ______________

## Phase 1: Basic UI
- Audience groups displayed: [ ] Pass [ ] Fail
- Cards show correct info: [ ] Pass [ ] Fail
- Buttons present: [ ] Pass [ ] Fail

## Phase 2: Group Chat UI
- Dialog opens: [ ] Pass [ ] Fail
- Sidebar shows personas: [ ] Pass [ ] Fail
- Chat area functional: [ ] Pass [ ] Fail

## Phase 3: Group Chat Functionality
- Text messages work: [ ] Pass [ ] Fail
- Staggered responses: [ ] Pass [ ] Fail
- Media upload works: [ ] Pass [ ] Fail

## Phase 4: Individual Chat
- Opens on persona click: [ ] Pass [ ] Fail
- 1-on-1 chat works: [ ] Pass [ ] Fail
- Media upload works: [ ] Pass [ ] Fail

## Phase 5: UI/UX
- Animations smooth: [ ] Pass [ ] Fail
- Dialogs work correctly: [ ] Pass [ ] Fail
- Messages display properly: [ ] Pass [ ] Fail

## Issues Found:
1. _______________________
2. _______________________
3. _______________________

## Overall Assessment:
[ ] Ready for production
[ ] Needs minor fixes
[ ] Needs major fixes

Notes:
_________________________
_________________________
```

---

## 🚨 Emergency Rollback

**If major issues found:**

1. **Stop frontend:**
   ```bash
   Ctrl+C in frontend terminal
   ```

2. **Revert changes:**
   ```bash
   cd frontend
   git checkout src/app/synthetic-audience/page.tsx
   git checkout src/components/audience/
   ```

3. **Restart:**
   ```bash
   npm run dev
   ```

---

## 📞 Next Steps After Testing

### If Testing PASSES:
1. Document any minor UI tweaks needed
2. Show client for feedback
3. Deploy to staging
4. Plan production deployment

### If Testing FAILS:
1. Document all issues in detail
2. Create GitHub issues for each problem
3. Fix critical bugs first
4. Re-test after fixes
5. Repeat until passing

---

**Ready to test! Good luck! 🚀**
