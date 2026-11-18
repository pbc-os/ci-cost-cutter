import {test,expect} from '@playwright/test';
test('a shopper can check out',async({page})=>{
  await page.goto('/cart');
  await page.click('text=Checkout');
  await page.waitForTimeout(500); // the payment form loads in an iframe
  await page.frameLocator('#pay').locator('#card').fill('4242424242424242');
  await page.click('text=Pay');
  await expect(page.locator('.receipt')).toBeVisible();
});
test('the cart total includes tax',async({page})=>{
  await page.goto('/cart');
  await expect(page.locator('.total')).toHaveText('$10.80');
});
