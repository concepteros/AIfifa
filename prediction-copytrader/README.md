# Prediction Copytrader

Standalone Chrome extension plus local Node executor for prediction-market monitoring and controlled copy-trading automation.

## Local Executor

```bash
npm run start:executor
```

The executor listens on `http://127.0.0.1:4787` by default.

## Chrome Extension

Load `prediction-copytrader/extension` as an unpacked extension in Chrome.

The dashboard opens from the extension action and calls the local executor status API.

## Verification

```bash
npm test
npm run check
```
