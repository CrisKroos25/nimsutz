import assert from 'node:assert/strict';
import test from 'node:test';
import { checkoutCard, formatCardNumber, formatExpiry, paymentAmount, paymentPeriod } from './paymentPresentation.js';

test('pasted card number is grouped without changing the API number', () => {
    const number = formatCardNumber('9999-0000-0000-0001');
    assert.equal(number, '9999 0000 0000 0001');
    const form = new FormData();
    Object.entries({ number, holder: 'NIM SUTZ DEMO', expiry: formatExpiry('1228'), security_code: '123' })
        .forEach(([name, value]) => form.set(name, value));
    assert.deepEqual(checkoutCard(form), {
        number: '9999000000000001', holder: 'NIM SUTZ DEMO',
        expiry_month: 12, expiry_year: 2028, security_code: '123',
    });
});

test('input formatting preserves leading zeros and limits digit counts', () => {
    assert.equal(formatCardNumber('0000000000000000123'), '0000 0000 0000 0000');
    assert.equal(formatExpiry('0129'), '01/29');
    assert.equal(formatExpiry('1'), '1');
    assert.equal(formatExpiry('12/28'), '12/28');
});

test('amounts preserve server decimals including zero; periods use Guatemala dates', () => {
    assert.equal(paymentAmount('0.00', 'GTQ'), 'Q0.00');
    assert.equal(paymentAmount('15.50', 'GTQ'), 'Q15.50');
    assert.equal(paymentAmount('15.50', 'USD'), '15.50 USD');
    const period = paymentPeriod('2026-10-01T02:00:00Z', '2026-11-01T02:00:00Z');
    assert.match(period, /30/);
    assert.match(period, /31/);
    assert.match(period, /2026/);
});
