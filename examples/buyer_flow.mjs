/*
 * TenderCouncil v2.1 buyer reference.
 *
 * This module only constructs real SDK call objects and read helpers. It never
 * calls client.writeContract, so importing or running static checks is safe.
 * Supply exact hashes of the bytes actually served at each URL.
 */

export const CHAIN_ID = 4221;
export const CORE = "0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd";
export const EVALUATOR = "0x023AB3434761715a531884Ca0852aC14beE03acE";
export const EVALUATOR_VERSION = "tendercouncil.evaluator.v2.1";

const assertSha256 = (value, field) => {
  if (!/^sha256:[0-9a-f]{64}$/.test(value)) {
    throw new Error(`${field} must be the exact lowercase sha256:<64 hex> digest`);
  }
};

const call = (functionName, args, value = 0n) => ({
  address: CORE,
  functionName,
  args,
  value,
  leaderOnly: false,
});

export async function inspectProduction(client) {
  const ready = await client.readContract({
    address: CORE,
    functionName: "get_production_ready",
    args: [],
  });
  const bindingText = await client.readContract({
    address: CORE,
    functionName: "get_evaluator_binding",
    args: [],
  });
  const binding = JSON.parse(bindingText);
  if (ready !== true || binding.bound !== true
      || binding.address.toLowerCase() !== EVALUATOR.toLowerCase()
      || binding.version !== EVALUATOR_VERSION) {
    throw new Error("production Core/Evaluator binding is not ready");
  }
  return { chainId: CHAIN_ID, core: CORE, evaluator: EVALUATOR, ready, binding };
}

export function createTenderCall({
  tenderId,
  title,
  briefUrl,
  briefSha256,
  maxBudgetWei,
  maxDeliveryDays,
  minSupportDays,
  biddingDeadline,
  responseWindowSeconds = 7200n,
  requirements,
  technicalWeight = 35,
  deliveryWeight = 20,
  priceWeight = 20,
  capabilityWeight = 15,
  supportWeight = 10,
  evidencePolicy,
}) {
  assertSha256(briefSha256, "briefSha256");
  const budget = BigInt(maxBudgetWei);
  return call("create_tender", [
    tenderId,
    title,
    briefUrl,
    briefSha256,
    budget,
    BigInt(maxDeliveryDays),
    BigInt(minSupportDays),
    BigInt(biddingDeadline),
    BigInt(responseWindowSeconds),
    requirements,
    technicalWeight,
    deliveryWeight,
    priceWeight,
    capabilityWeight,
    supportWeight,
    evidencePolicy,
  ], budget);
}

export const openTenderCall = (tenderId) => call("open_tender", [tenderId]);
export const closeTenderCall = (tenderId) => call("close_tender", [tenderId]);
export const startEvaluationCall = (tenderId) => call("start_evaluation", [tenderId]);
export const startResponseWindowCall = (tenderId) => call("start_response_window", [tenderId]);
export const advanceAfterResponseCall = (tenderId) => call("advance_after_response", [tenderId]);
export const settleAwardCall = (tenderId) => call("settle_award", [tenderId]);
export const confirmSettlementCall = (tenderId) => call("confirm_settlement", [tenderId]);
export const confirmRefundCall = (tenderId) => call("confirm_refund", [tenderId]);

export async function readBuyerState(client, tenderId, { includeEvaluatorResult = false } = {}) {
  const tender = await client.readContract({
    address: CORE,
    functionName: "get_tender",
    args: [tenderId],
  });
  const accounting = await client.readContract({
    address: CORE,
    functionName: "get_settlement_accounting",
    args: [tenderId],
  });
  const evaluationContext = await client.readContract({
    address: CORE,
    functionName: "get_evaluation_context",
    args: [tenderId],
  });
  let evaluationResult = null;
  if (includeEvaluatorResult && BigInt(tender.evaluation_nonce) > 0n) {
    evaluationResult = await client.readContract({
      address: EVALUATOR,
      functionName: "get_evaluation_result",
      args: [tenderId, BigInt(tender.evaluation_nonce)],
    });
  }
  return {
    tender,
    accounting: JSON.parse(accounting),
    evaluationContext: JSON.parse(evaluationContext),
    evaluationResult,
  };
}

// A real SDK write uses: await client.writeContract({ account, ...createTenderCall(params) }).
// Do that only in an application after a finalized/readback policy is in place.
