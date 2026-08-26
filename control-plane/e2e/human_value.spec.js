const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const artifactDir = path.join(process.cwd(), 'artifacts', 'human-value');

function field(world, name) {
  return world.locator(`[data-field="${name}"]`).innerText();
}

test('dynamic acquisition -> Ash -> LiveView -> human interaction -> receipt', async ({ page, context }) => {
  fs.mkdirSync(artifactDir, { recursive: true });
  const tracePath = path.join(artifactDir, 'human-value-trace.zip');
  const screenshotPath = path.join(artifactDir, 'human-value.png');

  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });

  try {
    await page.goto('/human-value');
    await expect(page.getByRole('heading', { name: 'Dynamic Ash value world' })).toBeVisible();
    await expect(page.getByTestId('world-count')).toContainText('0 runtime worlds');

    await page.getByRole('button', { name: 'Acquire synthetic value world' }).click();
    await expect(page.getByTestId('world-count')).toContainText('1 runtime worlds');

    let worlds = page.locator('[data-world]');
    await expect(worlds).toHaveCount(1);
    const first = worlds.first();

    const firstObservation = {
      scenario_id: await first.getAttribute('data-scenario-id'),
      seed: await first.getAttribute('data-seed'),
      provider: await first.getAttribute('data-provider'),
      ash_resource: await first.getAttribute('data-ash-resource'),
      organization: await field(first, 'organization'),
      opportunity: await field(first, 'opportunity'),
      revenue_from_customer: await field(first, 'revenue-from'),
      revenue_for_customer: await field(first, 'revenue-for'),
      evidence_class: await field(first, 'evidence-class'),
    };

    expect(firstObservation.provider).toBe('Elixir.ChatGPTCloud.HumanValue.Provider');
    expect(firstObservation.ash_resource).toBe('ChatGPTCloud.HumanValue.World');
    expect(firstObservation.evidence_class).toBe('SYNTHETIC');

    await page.getByRole('button', { name: 'Acquire synthetic value world' }).click();
    await expect(page.getByTestId('world-count')).toContainText('2 runtime worlds');

    worlds = page.locator('[data-world]');
    await expect(worlds).toHaveCount(2);
    const second = worlds.first();

    const secondObservation = {
      scenario_id: await second.getAttribute('data-scenario-id'),
      seed: await second.getAttribute('data-seed'),
      organization: await field(second, 'organization'),
      opportunity: await field(second, 'opportunity'),
      revenue_from_customer: await field(second, 'revenue-from'),
      revenue_for_customer: await field(second, 'revenue-for'),
    };

    expect(secondObservation.scenario_id).not.toBe(firstObservation.scenario_id);
    expect(secondObservation.seed).not.toBe(firstObservation.seed);
    expect(secondObservation.organization).not.toBe(firstObservation.organization);
    expect(secondObservation.opportunity).not.toBe(firstObservation.opportunity);
    expect(secondObservation.revenue_from_customer).not.toBe(firstObservation.revenue_from_customer);

    await second.getByRole('button', { name: 'Qualify' }).click();
    await expect(second.locator('[data-field="status"]')).toHaveText('qualified');
    await expect(second).toHaveAttribute('data-ash-action', 'qualify');

    const serverReceipt = JSON.parse(await page.getByTestId('value-receipt').innerText());
    expect(serverReceipt.scenario_id).toBe(secondObservation.scenario_id);
    expect(serverReceipt.seed.toString()).toBe(secondObservation.seed);
    expect(serverReceipt.ash_resource).toBe('ChatGPTCloud.HumanValue.World');
    expect(serverReceipt.ash_action).toBe('qualify');
    expect(serverReceipt.synthetic).toBe(true);
    expect(serverReceipt.rendered_values.organization).toBe(secondObservation.organization);
    expect(serverReceipt.rendered_values.opportunity).toBe(secondObservation.opportunity);
    expect(serverReceipt.rendered_values.status).toBe('qualified');

    await page.screenshot({ path: screenshotPath, fullPage: true });

    const receipt = {
      schema: 'human-value-playwright-receipt/v1',
      run_id: await page.locator('main[data-human-value-run]').getAttribute('data-human-value-run'),
      exact_head: process.env.PR_HEAD_SHA || process.env.GITHUB_SHA || 'UNKNOWN',
      journey: [
        'navigate:/human-value',
        'acquire:first',
        'observe:first-rendered-values',
        'acquire:second',
        'prove:runtime-variation',
        'qualify:second',
        'observe:ash-state-transition',
        'bind:server-receipt',
      ],
      dynamic_worlds: [firstObservation, secondObservation],
      server_receipt: serverReceipt,
      screenshot: 'human-value.png',
      trace: 'human-value-trace.zip',
      revenue_from_customer_evidence_class: 'SYNTHETIC_SOFTWARE_BEHAVIOR_ONLY',
      revenue_for_customer_evidence_class: 'SYNTHETIC_SOFTWARE_BEHAVIOR_ONLY',
      standing: 'VALUE_ALIVE',
    };

    fs.writeFileSync(
      path.join(artifactDir, 'human-value-playwright-receipt.json'),
      JSON.stringify(receipt, null, 2)
    );
  } finally {
    await context.tracing.stop({ path: tracePath });
  }
});
