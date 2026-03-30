# Production Release - Migration & Rollout Guide

## Release Overview

**Version**: 1.0.0 - Production Release with MS365 Authentication
**Release Date**: March 26, 2026
**Breaking Change**: Authentication now required (was optional in dev)

---

## Migration Timeline

### Phase 1: Preparation (Week 1)
- [ ] Test in staging environment
- [ ] Notify users of upcoming changes
- [ ] Prepare support documentation
- [ ] Train support team

### Phase 2: Pilot (Week 2)
- [ ] Deploy to 5-10 pilot users
- [ ] Gather feedback
- [ ] Fix any issues discovered
- [ ] Update documentation

### Phase 3: Rollout (Week 3-4)
- [ ] Deploy to 25% of users
- [ ] Monitor for issues
- [ ] Deploy to remaining users gradually
- [ ] Full deployment

---

## What Users Need to Know

### New Feature: Microsoft 365 Sign-In

**Benefits**:
- ✅ Secure authentication using your work account
- ✅ Automatic token management
- ✅ No more sharing login credentials
- ✅ Better audit trail and compliance

**What Changed**:
- Users must sign in with Microsoft 365 account (@company.com)
- First use requires accepting app permissions
- Session persists between app restarts
- Automatic logout after 24 hours

### User Requirements

- Microsoft 365 work/school account
- Internet connection for first sign-in
- Phone or browser to complete sign-in

### Not Affected

- When users sign in, they remain logged in
- Existing data is preserved
- UI and features remain the same
- Works offline (after initial signin)

---

## Step-by-Step User Migration

### For New Users

1. **Launch App**
   - Tap "Sign in with Microsoft 365"

2. **Sign In**
   - Enter your work email (user@company.com)
   - Enter password
   - Complete verification if prompted

3. **Grant Permissions**
   - Review requested permissions
   - Tap "Accept"

4. **Start Using**
   - You're logged in!
   - Start logging student points

### For Existing Users Upgrading

1. **Update App**
   - Update to v1.0.0 from app store
   - Or rebuild if using development version

2. **First Launch**
   - You'll see the new Sign In screen
   - Previous session data is not lost

3. **Sign In**
   - Follow steps in "For New Users" above

4. **Your Previous Data**
   - Previous entries are still available
   - Data synced to SharePoint as before

---

## Support Communication

### Email Template

```
Subject: Awana Points Logger Update - Sign In Required

Hi [Team],

We're releasing an important security update to the Awana Points Logger 
app this week. Here's what you need to know:

📦 What's New:
- Secure Microsoft 365 sign-in (using your work account)
- Automatic session management
- Better security and audit trail

🔐 You'll Need:
- Your Microsoft 365 work email
- Internet connection for first sign-in

✓ Your Action:
1. Update app to v1.0.0
2. Sign in with your work email
3. Accept permissions
4. Start logging points as normal

❓ Questions?
Contact [support email] or reply to this message.

Thanks,
[Your Team]
```

### FAQ for Users

**Q: Do I need a new login?**
A: Yes, use your Microsoft 365 work email (user@company.com)

**Q: Will I lose my data?**
A: No, all previous data is preserved and synced to SharePoint

**Q: What permissions is the app asking for?**
A: User profile and email (for identification and auditing)

**Q: What if I forget my password?**
A: Use the standard Microsoft 365 password reset at outlook.com

**Q: Can I still use the app offline?**
A: After signing in once, you can work offline until tokens expire

**Q: How long does my session last?**
A: 24 hours. You'll need to sign in again after that.

**Q: What if I'm having issues?**
A: Check your internet, try updating the app, or contact support

---

## Rollout Checklist

### Pre-Rollout
- [ ] All tests passing
- [ ] Documentation finalized
- [ ] Support team trained
- [ ] Rollback plan documented
- [ ] Monitoring set up

### Rollout Day
- [ ] Announce release in channels
- [ ] Deploy backend updates
- [ ] Deploy frontend updates
- [ ] Monitor for errors
- [ ] Send user instructions

### Post-Rollout
- [ ] Check error logs
- [ ] Monitor API performance
- [ ] Respond to support tickets
- [ ] Gather user feedback
- [ ] Plan improvements

---

## Rollback Plan

### If Critical Issues Found

```bash
# Revert to previous version
1. Stop deployment
2. Investigate error
3. Check logs: /var/log/awana-api.log
4. If critical: restore backup
5. Notify users of delay
6. Fix issue
7. Re-deploy
```

### User Communication for Rollback

```
Subject: Technical Issue - Service Temporarily Unavailable

We're experiencing technical difficulties and have temporarily 
rolled back to the previous version while we fix the issue.

Expected Resolution: [Time]

We apologize for the inconvenience.
```

---

## Monitoring Post-Rollout

### Key Metrics

- **Login Success Rate**: Target > 99%
- **API Response Time**: Target < 500ms
- **Error Rate**: Target < 0.1%
- **Token Refresh Success**: Target > 99.9%

### Daily Checks

```bash
# Check backend health
curl https://api.yourdomain.com/health

# Check logs for errors
docker logs awana-api | grep ERROR

# Monitor active users
# Check dashboard at your monitoring tool
```

### Weekly Review

- Token refresh statistics
- Failed authentications
- Performance metrics
- User feedback
- Error patterns

---

## Documentation for Support Team

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Invalid Login" | Wrong email | Verify user entered correct work email |
| "Permission Denied" | Account not provisioned | Add user to security group in Azure AD |
| "Can't Connect" | Network issue | Check internet connection |
| "Keep Signing Out" | App crash | Clear app cache and reinstall |

### Escalation Process

1. **User Contact**: Support team
2. **Support Investigation**: Check app logs, user account status
3. **Escalate if**: Issue not resolved in 30 minutes
4. **Technical Team**: Investigate server logs, database
5. **Azure AD Team**: If authentication issue

### Support Contacts

- **App Support**: [Support Email]
- **Azure AD Admin**: [Admin Email]
- **Backend Ops**: [Ops Email]
- **On-Call Engineer**: [Engineer Contact]

---

## Post-Release Improvements

### Planned for v1.1.0

- [ ] Biometric sign-in (fingerprint/face)
- [ ] Offline mode improvements
- [ ] Performance optimizations
- [ ] Additional languages
- [ ] Dark mode support

### Community Feedback

Gather feedback via:
- In-app feedback button
- Email survey
- Support tickets
- Weekly sync meetings

---

## Success Criteria

✅ **Successful Rollout When**:
- > 95% of users successfully signed in
- < 0.1% error rate on production
- No critical issues reported
- Users can complete workflows as before
- Support team handling questions

❌ **Rollback Triggers**:
- > 5% sign-in failure rate
- API response time > 5 seconds
- Data loss or corruption
- Security vulnerability discovered

---

## Communication Timeline

| Date | What | Who | Channel |
|------|------|-----|---------|
| T-7d | Announcement | All managers | Email + Slack |
| T-3d | Reminder + FAQ | All users | Email + App notification |
| T-1d | Final prep | Support + Tech | Slack |
| T+0 | Release + Monitoring | Tech team | Incident channel |
| T+1h | Update status | All users | Email |
| T+1d | Thank you + feedback | All users | Email |

---

## Documentation References

- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT_GUIDE.md)
- [Azure AD Configuration](./AZURE_AD_SETUP.md)
- [MSAL Quick Reference](./MSAL_QUICK_REFERENCE.md)
- [User Guide](./USER_GUIDE.md)

---

**Release Manager**: [Your Name]
**Release Date**: March 26, 2026
**Version**: 1.0.0
**Status**: Ready for Production
