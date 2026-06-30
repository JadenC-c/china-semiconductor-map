import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const profile = await mkdtemp(join(tmpdir(), "silicon-map-qa-"));
const port = 9339;
const url = pathToFileURL(resolve("dist/index.html")).href;
const chrome = spawn(chromePath, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--remote-allow-origins=*",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, url
], { stdio: "ignore" });

const sleep = ms => new Promise(resolvePromise => setTimeout(resolvePromise, ms));
let target;
for (let attempt = 0; attempt < 50; attempt += 1) {
  try {
    const targets = await fetch(`http://127.0.0.1:${port}/json`).then(response => response.json());
    target = targets.find(item => item.type === "page");
    if (target) break;
  } catch {}
  await sleep(100);
}
if (!target) throw new Error("Chrome 调试目标未就绪");

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolvePromise, reject) => {
  ws.addEventListener("open", resolvePromise, { once: true });
  ws.addEventListener("error", reject, { once: true });
});

let id = 0;
const pending = new Map();
ws.addEventListener("message", event => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve: resolvePromise, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolvePromise(message.result);
});

function command(method, params = {}) {
  const commandId = ++id;
  ws.send(JSON.stringify({ id: commandId, method, params }));
  return new Promise((resolvePromise, reject) => pending.set(commandId, { resolve: resolvePromise, reject }));
}

async function evaluate(expression) {
  const result = await command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

for (let attempt = 0; attempt < 50; attempt += 1) {
  if (await evaluate("document.readyState === 'complete' && document.querySelectorAll('.map-node').length === 20")) break;
  await sleep(100);
}

const checks = [];
checks.push(["20 个产业节点", await evaluate("document.querySelectorAll('.map-node').length === 20")]);
checks.push(["首屏 24 张公司卡", await evaluate("document.querySelectorAll('.company-card').length === 24")]);
checks.push(["点击 CPO 节点", await evaluate("document.querySelector('[data-node=\"cpo\"]').click(); document.querySelector('#nodeInspector h3').textContent === 'CPO'")]);
checks.push(["节点联动公司筛选", await evaluate("document.querySelector('#nodeFilter').value === 'cpo' && document.querySelectorAll('.company-card').length === 4")]);
checks.push(["打开公司详情", await evaluate("new Promise(resolve=>{document.querySelector('.company-card').click(); setTimeout(()=>resolve(document.querySelector('#companyDrawer').classList.contains('open') && document.querySelectorAll('[data-metric]').length === 6 && !!document.querySelector('.financial-chart')),60)})")]);
checks.push(["切换净利润图", await evaluate("document.querySelector('[data-metric=\"netProfit\"]').click(); document.querySelector('[data-metric=\"netProfit\"]').classList.contains('active') && !!document.querySelector('.financial-chart')")]);
await evaluate("document.querySelector('#closeDrawer').click()");
checks.push(["股票代码搜索", await evaluate("(()=>{document.querySelector('#nodeFilter').value='all'; document.querySelector('#nodeFilter').dispatchEvent(new Event('change',{bubbles:true})); const i=document.querySelector('#companySearch'); i.value='688256'; i.dispatchEvent(new Event('input',{bubbles:true})); return document.querySelectorAll('.company-card').length === 1 && document.querySelector('.company-card').textContent.includes('688256')})()")]);
checks.push(["港股筛选仅返回双重上市主体", await evaluate("(()=>{const i=document.querySelector('#companySearch'); i.value=''; i.dispatchEvent(new Event('input',{bubbles:true})); document.querySelector('[data-market=\"H\"]').click(); return document.querySelectorAll('.company-card').length === 2})()")]);

await command("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await sleep(150);
checks.push(["390px 页面无横向溢出", await evaluate("document.documentElement.scrollWidth <= window.innerWidth")]);

for (const [name, passed] of checks) console.log(`${passed ? "PASS" : "FAIL"}: ${name}`);
const failed = checks.filter(([, passed]) => !passed);
ws.close();
chrome.kill();
await sleep(250);
await rm(profile, { recursive: true, force: true }).catch(() => {});
if (failed.length) process.exitCode = 1;
