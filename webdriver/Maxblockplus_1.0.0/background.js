/*
 * extension process crashes or your extension is manually stopped at
 * chrome://serviceworker-internals
 */
'use strict';

chrome.declarativeNetRequest.onRuleMatchedDebug.addListener((e) => {
    const msg = `Navigation blocked to ${e.request.url} on tab ${e.request.tabId}.`;
    //console.log(msg);
});

// settings.json is a single shared master file (hardlink to app root), it
// never carries extension-specific keys. Use the built-in filter list when
// the master does not provide one.
const DEFAULT_DOMAIN_FILTER = [
"*.doubleclick.net/*",
"*.googlesyndication.com/*",
"*.ssp.hinet.net/*",
"*a.amnet.tw/*",
"*adx.c.appier.net/*",
"*cdn.cookielaw.org/*",
"*cdnjs.cloudflare.com/ajax/libs/clipboard.js/*",
"*clarity.ms/*",
"*cloudfront.com/*",
"*cms.analytics.yahoo.com/*",
"*e2elog.fetnet.net/*",
"*fundingchoicesmessages.google.com/*",
"*ghtinc.com/*",
"*google-analytics.com/*",
"*googletagmanager.com/*",
"*googletagservices.com/*",
"*img.uniicreative.com/*",
"*lndata.com/*",
"*match.adsrvr.org/*",
"*onead.onevision.com.tw/*",
"*play.google.com/log?*",
"*popin.cc/*",
"*rollbar.com/*",
"*sb.scorecardresearch.com/*",
"*tagtoo.co/*",
"*ticketmaster.sg/js/adblock*",
"*ticketmaster.sg/js/adblock.js*",
"*tixcraft.com/js/analytics.js*",
"*tixcraft.com/js/common.js*",
"*tixcraft.com/js/custom.js*",
"*treasuredata.com/*",
"*www.youtube.com/youtubei/v1/player/heartbeat*",
];

function reload_rule_from_setting(settings)
{
    if(!settings.hasOwnProperty("domain_filter")) {
        settings.domain_filter = DEFAULT_DOMAIN_FILTER;
    }
    initializeDynamicRules(settings.domain_filter);
}

chrome.runtime.onInstalled.addListener(function(){
    fetch("data/settings.json")
    .then((resp) => resp.json())
    .then((settings) =>
    {
        reload_rule_from_setting(settings);

        chrome.storage.local.set(
        {
            settings: settings,
        });
        console.log("dump settings.json to extension storage");
    }
    ).catch(error =>
    {
        console.log('error is', error)
    }
    );
});

function initializeDynamicRules(domain_filter)
{
    const base_rule = {
        "id" : 1,
        "priority": 1,
        "action" : { "type" : "block" },
        "condition" : {
            "urlFilter": "",
            "resourceTypes" : ["main_frame", "sub_frame", "script", "image", "font", "xmlhttprequest", "media", "stylesheet"]
    }};

    let formated_rules = [];

    for(let i=0; i<domain_filter.length; i++) {
        let new_rule = {};
        Object.assign(new_rule, base_rule);
        new_rule.condition.urlFilter = domain_filter[i];
        new_rule.id = i+1;
        formated_rules.push(new_rule);
    }
    
    let roles = {
        removeRuleIds:[],
        addRules: formated_rules
    };

    const oldRules = chrome.declarativeNetRequest.getDynamicRules();
    
    //console.log(oldRules);
    oldRules.then(function(result) {
        // here you can use the result of promiseB
        //console.log(result);
        let removeRuleIds=[]
        for(let i=0; i<result.length; i++) {
            removeRuleIds.push(result[i].id);
        }
        roles.removeRuleIds = removeRuleIds;
        //console.log(roles);
        chrome.declarativeNetRequest.updateDynamicRules(roles,function(){});
    });  
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    let request_json = request;
    let result_json={"answer": "pong from background"};
    if(request_json.action=="update_role") {
        reload_rule_from_setting(request_json.data.settings);
        result_json={"answer": "updating"};
        sendResponse(result_json);
    }
});
