/*
 * Copyright 2019 Peifeng Yu <peifeng@umich.edu>
 * 
 * This file is part of Salus
 * (see https://github.com/SymbioticLab/Salus).
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *    http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "resources/iteralloctracker.h"
#include "utils/date.h"
#include "platform/logging.h"

using std::chrono::duration_cast;
using std::chrono::microseconds;
using std::chrono::milliseconds;
using std::chrono::nanoseconds;
using std::chrono::seconds;
using std::chrono::system_clock;
using FpSeconds = std::chrono::duration<double, seconds::period>;
using namespace std::chrono_literals;
using namespace date;

namespace salus {

IterAllocTracker::IterAllocTracker(const ResourceTag &tag, size_t window, double peakthr)
    : m_tag(tag)
    , m_peakthr(peakthr)
    , m_window(window)
{
}

bool IterAllocTracker::beginIter(AllocationRegulator::Ticket ticket, ResStats estimation, uint64_t currentUsage)
{
    if (m_holding) {
        return false;
    }

    m_ticket = ticket;
    if (m_numIters == 0) {
        m_est = estimation;
    }

    VLOG(3) << "IterAllocTracker@" << as_hex(this) << "::beginIter ticket=" << m_ticket.as_int
            << ", estimation=" << m_est.DebugString() << ", numIter=" << m_numIters;

    // reset curr
    m_currPersist = currentUsage;
    m_currPeak = 0;
    m_count = 0;

    // reset buffer
    m_buf.clear();
    if (m_window == 0 && m_est.count != 0) {
        auto cap = std::max(m_est.count / 50, size_t{2});
        m_buf.set_capacity(cap);
    } else if (m_window == 0){
        m_buf.set_capacity(50);
    } else {
        m_buf.set_capacity(m_window);
    }

    // reserve res
    Resources cap;
    cap[m_tag] = m_est.temporary;
    VLOG(3) << "IterAllocTracker@" << as_hex(this) << " reserve: " << cap;
    m_holding = m_ticket.beginAllocation(cap);
    if (m_holding) {
        ++m_numIters;
    } else {
        // to avoid deadlock
        auto str = m_ticket.DebugString();
        VLOG(2) << "Delay iteration due to unsafe resource usage@" << as_hex(this) << ". Ticket: " << m_ticket.as_int << ", Predicted usage: "
                << cap << ", current usage: " << str;
    }
    return m_holding;
}

bool IterAllocTracker::update(size_t num)
{
    m_currPeak = std::max(m_currPeak, num);
    ++m_count;

    VLOG(3) << "IterAllocTracker@" << as_hex(this) << "::update ticket=" << m_ticket.as_int << ", numIter=" << m_numIters
            << ", current=" << m_currPersist << ", peak=" << m_currPeak << ", count=" << m_count;

    if (!m_holding) {
        return false;
    }

#if defined(SALUS_ENABLE_EXCLUSIVE_ITER)
    return false;
#else
    // If we hold memory allocation, estimate when we should release it
    m_buf.push_back({system_clock::now().time_since_epoch().count(), num});

    if (m_buf.size() < 2) {
        return false;
    }

    auto [stx, sty] = m_buf.front();
    auto [edx, edy] = m_buf.back();
    auto slope = (edy - sty) * 1.0 / (edx - stx);
    if (slope < 0 && num >= m_peakthr * m_est.temporary) {
        releaseAllocationHold();
        return true;
    }

    return false;
#endif
}

void IterAllocTracker::releaseAllocationHold()
{
    if (!m_holding) {
        return;
    }

    m_holding = false;

    Resources toRelease{
        {m_tag, m_est.temporary}
    };
    VLOG(3) << "IterAllocTracker@" << as_hex(this) << "::endIter ticket=" << m_ticket.as_int << ", estimation=" << m_est.DebugString()
            << ", numIter=" << m_numIters << ", toRelease=" << toRelease;
    m_ticket.endAllocation(toRelease);
}

namespace {
size_t runningAvg(size_t lastAvg, size_t current, int newCount)
{
    if (lastAvg == 0 || newCount == 0) {
        return current;
    }

    double avg = lastAvg;
    avg = (avg * (newCount - 1) + current) / newCount;
    return static_cast<size_t>(avg);
}
}

void IterAllocTracker::endIter()
{
    // first release hold, because we'll be modifying m_est
    releaseAllocationHold();

    // update our estimation using running average

    // persist usage
    if (m_currPeak > m_currPersist) {
        auto newTemporary = m_currPeak - m_currPersist;
        m_est.temporary = runningAvg(m_est.temporary, newTemporary, m_numIters);
    }
    m_est.count = runningAvg(m_est.count, m_count, m_numIters);
}

} // namespace salus
