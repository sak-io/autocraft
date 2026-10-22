# Spec: ClassBook

**Status:** AGREED  ·  **Owner:** Maya (Lotus Yoga)  ·  **Date:** 2026-10-10
**Phase covered:** Phase 1 (MVP: browse, book, cancel, manage classes, confirmation emails). Payments are a later phase.

## 1. Problem & goal
Lotus Yoga is a small studio run by Maya. Students cannot easily see which classes exist or reserve a place, and classes have limited spots. ClassBook lets students see upcoming classes, book a spot and cancel it, and lets Maya add and manage classes herself, with no one ever booked into a full class.

**Also needed (capabilities detected):** secrets-and-config, deployment-hosting, analytics-observability (always); authentication (words: "students", "book", "myself" implies an admin); database ("limited spots" must be remembered). email-and-notifications (booking and cancellation confirmations, Q4). Maya has confirmed; add authentication, database and email-and-notifications to `.autocraft/config.yml`.

**Security/privacy flags for Architect and Security Auditor:** student accounts hold personal data (name, email). Only the studio admin may create or change classes. Students may only see and cancel their own bookings. No payment data in phase 1.

## 2. Actors
- **Visitor**: anyone not signed in; can see the class schedule.
- **Student**: signed-in person; books and cancels their own spots.
- **Admin (Maya, the single admin account in phase 1)**: manages classes and sees who is booked.

## 3. User stories & acceptance criteria

### US-1: As a visitor I want to see upcoming classes so that I can choose one
- AC-1.1 **Given** classes exist starting within the next 60 days **When** a visitor opens the schedule **Then** each class starting within 30 days shows title, start date/time, duration, instructor, and spots left, ordered by start time; classes starting more than 30 days ahead are shown greyed with title, start date/time, duration, instructor and the opens-on date, and do NOT show spots left (see AC-1.5); classes beyond 60 days are not listed.
- AC-1.2 **Given** a class whose start time has passed or that was cancelled by the admin **When** the schedule is viewed **Then** it is not listed. Classes starting more than 30 days ahead (within 60) are NOT excluded; they are listed greyed.
- AC-1.3 **Given** no upcoming classes **When** the schedule is viewed **Then** a friendly empty message is shown.
- AC-1.4 **Given** a class is full **When** the schedule is viewed **Then** it shows "Full" and offers no book action.
- AC-1.5 **Given** a class starting more than 30 days from now (within 60) **When** the schedule is viewed **Then** it is greyed, shows "Opens for booking on <date and time, Europe/London>" (the class start minus 30 days), does not show spots left, and has no Book action.

### US-2: As a visitor I want to create an account and sign in so that I can book
- AC-2.1 **Given** a new email **When** the visitor signs up with valid details **Then** an account is created and they are signed in.
- AC-2.2 **Given** an already-used email **When** someone signs up **Then** it is rejected without revealing more than necessary.
- AC-2.3 **Given** a signed-out visitor **When** they try to book **Then** they are asked to sign in and, after signing in, return to that class.
- AC-2.4 **Given** wrong credentials **When** signing in **Then** access is denied with a generic message.

### US-3: As a student I want to book a spot so that my place is guaranteed
- AC-3.1 **Given** a signed-in student and a class with spots left **When** they book **Then** a booking is created and spots left drops by 1.
- AC-3.2 **Given** a class with 0 spots left **When** a student books **Then** the booking is refused with a "class is full" message and no booking exists.
- AC-3.3 **Given** a class with 1 spot left **When** two students book at the same moment **Then** exactly one succeeds and the other is told it is full (spots never go below 0).
- AC-3.4 **Given** a student already booked on a class **When** they book it again **Then** no second booking is created.
- AC-3.5 **Given** a class that has already started or been cancelled **When** a student tries to book it (including by calling the server directly) **Then** it is refused.
- AC-3.6 **Given** a class starting within the next 30 days **When** a student books it **Then** it is allowed; **Given** a class starting more than 30 days from now **Then** it is shown but not bookable, with its opens-on date; a direct booking attempt is refused with an explanation.
- AC-3.7 **Given** a class more than 30 days away **When** time passes so it starts within 30 days **Then** the greyed "Opens for booking" label disappears and the Book action appears automatically, without any admin action.

### US-4: As a student I want to see and cancel my bookings so that I free my spot if my plans change
- AC-4.1 **Given** a student with bookings **When** they open "My bookings" **Then** they see only their own upcoming bookings; upcoming bookings whose class was cancelled by the studio are also shown, marked "cancelled by the studio".
- AC-4.2 **Given** a booking for a class starting at least 12 hours from now (Q2) **When** the student cancels **Then** the booking is removed and spots left rises by 1.
- AC-4.3 **Given** a class starting less than 12 hours from now (exactly 12 hours is allowed) or already started **When** the student cancels **Then** it is refused with an explanation and the booking and spots left are unchanged.
- AC-4.4 **Given** student A **When** A tries to view or cancel student B's booking (by direct request) **Then** it is refused and nothing changes.
- AC-4.5 **Given** a booking already cancelled **When** cancelled again **Then** spots left does not change a second time.

### US-4b: As a student I want a confirmation email when I book or cancel so that I have a record
- AC-4b.1 **Given** a successful booking **When** it is created **Then** one confirmation message is sent to the student's email containing class title, date/time (Europe/London) and "booked".
- AC-4b.2 **Given** a successful cancellation **When** it completes **Then** one cancellation message is sent containing the class title, date/time and "cancelled".
- AC-4b.3 **Given** the mailer fails or is unavailable **When** a student books or cancels **Then** the booking/cancellation still succeeds, spots left is correct, and the failure is logged.
- AC-4b.4 **Given** a refused booking or cancellation (full, too late, duplicate) **When** it is refused **Then** no email is sent.
- AC-4b.5 **Given** the same booking request is repeated (e.g. double click) **When** the second is a duplicate **Then** only one email is sent.
- AC-4b.6 **Given** phase 1 **When** messages are sent **Then** they go through a replaceable mailer that records each message (recipient, subject, body) so tests can check them; real delivery is connected later without changing the rules above. Test environments never email real people.

### US-5: As an admin I want to add classes so that students can book them
- AC-5.1 **Given** a signed-in admin **When** they submit title, start date/time, duration, instructor and capacity (whole number >= 1) **Then** the class appears on the schedule with all spots free.
- AC-5.2 **Given** missing or invalid fields (blank title, capacity 0 or negative, start in the past) **When** submitted **Then** nothing is saved and the problems are shown per field.
- AC-5.3 **Given** a student or visitor **When** they try to open the add-class page or submit it directly **Then** access is denied and nothing is created.

### US-6: As an admin I want to edit or cancel a class and see who is booked so that I can run the studio
- AC-6.1 **Given** a class with bookings **When** the admin views it **Then** they see the list of booked students (name, email) and spots left.
- AC-6.2 **Given** a class with N bookings **When** the admin lowers capacity below N **Then** the change is refused with an explanation.
- AC-6.3 **Given** a class with bookings **When** the admin cancels the class **Then** it is no longer bookable and its bookings are marked cancelled (students are not notified automatically, Q5), and they appear in each student's My bookings marked "cancelled by the studio" (still no email).
- AC-6.4 **Given** a non-admin **When** they try to edit or cancel a class **Then** access is denied.

## 4. Non-goals (out of scope for phase 1)
- Payments, class packs, memberships, refunds (later phase).
- Waitlists, recurring/repeating classes (each class added one at a time), multi-room or multi-studio.
- Reminder emails, SMS, push notifications, and automatic emails to students when Maya cancels a class (Q5).
- Real email delivery in phase 1 (messages are recorded only; see AC-4b.6).
- Staff/extra admin accounts (Maya adds staff later).
- Social sign-in, mobile apps, calendar sync, reviews, instructor accounts.
- Reports/analytics dashboards for Maya beyond the booked-students list.
- Languages other than English; multiple time zones (studio time zone only).

## 5. Non-functional needs
| Area | Need | Assumed? |
|---|---|---|
| Load | < 1,000 students in year one; ~20 classes/week; bursts of ~50 people booking at once when a popular class opens | yes |
| Latency | schedule and booking respond in under 1 s (p95) | yes |
| Availability | 99% is enough; short outages acceptable | yes |
| Data sensitivity | personal (name, email, booking history); no payment data | yes |
| Admin sign-in | admin password minimum 14 characters. ACCEPTED RISK: no MFA and no automatic password reset for the admin; Maya's nephew Tom resets it by hand | answered (Q1) |
| Compliance | treat as privacy-law aware (GDPR-style): student can ask for account deletion (manual in phase 1) | yes |
| Accessibility | usable on phones and by keyboard; basic accessibility checks pass | yes |
| Correctness | spots left is never negative and never out of sync with bookings | required |
| Time zone | all times shown and compared in Europe/London | answered (Q6) |
| Budget | free or very low-cost hosting tier | yes |
| Token efficiency | the team builds and maintains ClassBook within a stated token budget (token_mode: lean) | process |

## 6. Assumptions & open questions
Maya could not be asked in this run; each default below was used. Please answer "yes, default" or correct it.

Maya answered all questions (status: ANSWERED).

- **Q1** ANSWERED: email + password. Maya is the single admin account; staff accounts later (out of scope). Admin password minimum 14 characters. Accepted risk: no MFA and no automatic password reset; Maya's nephew Tom resets it by hand.
- **Q2** ANSWERED: students must cancel at least 12 hours before class start (changed from 2 hours, so Maya does not lose the spot).
- **Q3** ANSWERED: default accepted; one spot per student per class, no guests.
- **Q4** ANSWERED: yes to confirmation emails on booking and on cancellation (US-4b); reminders later. Constraint: no real mail service is available now, so phase 1 uses a replaceable mailer that records messages; real delivery connected later. An email failure must never fail or roll back a booking.
- **Q5** ANSWERED: default accepted; cancelled classes mark bookings cancelled, Maya tells students herself.
- **Q6** ANSWERED: one time zone, Europe/London.
- **Q7** ANSWERED: bookable only for classes starting within the next 30 days (AC-3.6, AC-3.7).
- **Q8** ANSWERED by assumption (flag for Maya to confirm): the schedule lists classes up to 60 days ahead; those beyond 30 days are greyed and not bookable (AC-1.1, AC-1.5).

## Change log
- 2026-10-10: Scope change agreed with Maya: schedule shows next month's classes greyed with "Opens for booking on <date>" (60-day listing horizon, Q8); studio-cancelled bookings show in My bookings (no email); admin password min 14 chars, no MFA / manual reset accepted (Q1).
- 2026-10-10: Clarified AC-1.1/AC-1.5 after QA: greyed classes beyond 30 days do NOT show spots left. Reason (Maya): nobody can book them yet and it would only confuse people.
